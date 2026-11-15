"""Dịch vụ đơn hàng: báo giá, đặt hàng, giao hàng, hoàn tất, hủy."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable

from ..exceptions import NotFoundError, OutOfStockError, ValidationError
from ..models import (
    DEFAULT_IDS,
    Cart,
    Customer,
    DiscountPolicy,
    DiscountRegistry,
    IdGenerator,
    MembershipPlan,
    NoDiscount,
    Order,
    OrderLine,
    OrderQuote,
    OrderStatus,
    OrderType,
    Voucher,
)
from .events import OrderListener
from .inventory import InventoryService
from .vouchers import VoucherService


class OrderService:
    PAYMENT_METHODS = ("Thanh toán khi nhận hàng (COD)", "Chuyển khoản ngân hàng")

    def __init__(
        self,
        inventory: InventoryService,
        discounts: DiscountRegistry,
        vouchers: VoucherService,
        orders: Iterable[Order] = (),
        clock: Callable[[], datetime] = datetime.now,
        ids: IdGenerator = DEFAULT_IDS,
    ) -> None:
        self._ids = ids
        self._inventory = inventory
        self._discounts = discounts
        self._vouchers = vouchers
        self._orders: list[Order] = list(orders)  # thứ tự thêm vào (cũ → mới)
        self._clock = clock
        self._listeners: list[OrderListener] = []

    # ------------------------------------------------------------- Observer
    def add_listener(self, listener: OrderListener) -> None:
        self._listeners.append(listener)

    # -------------------------------------------------------------- truy vấn
    def stored(self) -> list[Order]:
        """Danh sách theo thứ tự lưu trữ (cũ → mới) – dùng khi ghi dữ liệu."""
        return list(self._orders)

    def all(self) -> list[Order]:
        """Mới nhất trước; cùng thời điểm thì đơn tạo sau đứng trước."""
        ranked = sorted(enumerate(self._orders), key=lambda pair: (pair[1].created_at, pair[0]), reverse=True)
        return [order for _, order in ranked]

    def _new_order(self, **fields) -> Order:
        """Tạo đơn với mã chưa dùng (mã có ngày đặt: HD-yymmdd-XXXXXXXX)."""
        created_at = self._clock()
        order_id = self._ids.new_id(Order.id_prefix(created_at), lambda candidate: self.find(candidate) is not None)
        return Order(order_id=order_id, created_at=created_at, **fields)

    def find(self, order_id: str | None) -> Order | None:
        return next((o for o in self._orders if o.id == order_id), None)

    def get(self, order_id: str) -> Order:
        order = self.find(order_id)
        if order is None:
            raise NotFoundError(f"Không tìm thấy đơn hàng '{order_id}'")
        return order

    def by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self.all() if o.customer_id == customer_id]

    def by_status(self, *statuses: OrderStatus | None) -> list[Order]:
        wanted = {s for s in statuses if s is not None}
        return [o for o in self.all() if not wanted or o.status in wanted]

    def count(self, *statuses: OrderStatus) -> int:
        """Đếm đơn theo trạng thái – không cần sắp xếp (dùng ở thanh menu, chạy mỗi request)."""
        wanted = set(statuses)
        return sum(1 for o in self._orders if o.status in wanted)

    def __len__(self) -> int:
        return len(self._orders)

    # ------------------------------------------------------------- báo giá
    def quote(
        self,
        cart: Cart,
        customer: Customer | None,
        order_type: OrderType = OrderType.ONLINE,
        voucher: Voucher | None = None,
    ) -> OrderQuote:
        """Chọn ưu đãi có lợi nhất giữa các chính sách tự động và mã khách nhập (không cộng dồn)."""
        subtotal = cart.subtotal()
        quantity = cart.total_quantity()
        candidates: list[DiscountPolicy] = [self._discounts.best_for(subtotal, customer, quantity)]
        if voucher is not None:
            candidates.append(voucher)
        policy = max(candidates, key=lambda p: p.calculate(subtotal, customer, quantity))
        discount = min(subtotal, policy.calculate(subtotal, customer, quantity))
        shipping = 0.0
        if order_type.charges_shipping:
            shipping = max((product.shipping_fee() for product, _ in cart.items()), default=0.0)
        return OrderQuote(subtotal, discount, shipping, policy.code, policy.description,
                          voucher.code if voucher else "")

    # ------------------------------------------------------------- đặt hàng
    def place_order(
        self,
        cart: Cart,
        *,
        customer: Customer,
        payment_method: str,
        shipping_address: str,
        contact_phone: str = "",
        voucher_code: str = "",
    ) -> Order:
        if cart.is_empty():
            raise ValidationError("Giỏ hàng đang trống")
        if payment_method not in self.PAYMENT_METHODS:
            raise ValidationError("Phương thức thanh toán không hợp lệ")
        if not shipping_address.strip():
            raise ValidationError("Vui lòng nhập địa chỉ nhận hàng")

        # Bước 1: kiểm tra TOÀN BỘ trước khi thay đổi bất kỳ dữ liệu nào.
        for product, quantity in cart.items():
            if self._inventory.find(product.id) is not product:
                raise NotFoundError(f"'{product.title}' không còn bán, hãy xóa khỏi giỏ")
            if not product.can_supply(quantity):
                raise OutOfStockError(f"'{product.title}' chỉ còn {product.stock_label()}, không đủ {quantity}")
        voucher = self._vouchers.validate(voucher_code, cart.subtotal()) if voucher_code.strip() else None

        quote = self.quote(cart, customer, OrderType.ONLINE, voucher)
        order = self._new_order(
            order_type=OrderType.ONLINE,
            lines=cart.to_lines(),
            payment_method=payment_method,
            customer_id=customer.id,
            customer_name=customer.name,
            contact_phone=contact_phone.strip() or customer.phone,
            discount_code=quote.policy_code,
            discount_description=quote.policy_description,
            discount_amount=quote.discount_amount,
            shipping_fee=quote.shipping_fee,
            shipping_address=shipping_address,
        )

        # Bước 2: mọi thứ hợp lệ mới giữ hàng, trừ lượt dùng mã và ghi nhận đơn.
        for product, quantity in cart.items():
            product.take_from_stock(quantity)
        if voucher is not None and quote.voucher_applied:
            voucher.use()
        self._orders.append(order)
        cart.clear()
        return order

    def record_membership(self, customer: Customer, plan: MembershipPlan, payment_method: str) -> Order:
        policy = self._discounts.get(NoDiscount.CODE)
        order = self._new_order(
            order_type=OrderType.MEMBERSHIP,
            lines=[OrderLine.from_product(plan, 1)],
            payment_method=payment_method,
            customer_id=customer.id,
            customer_name=customer.name,
            contact_phone=customer.phone,
            discount_code=policy.code,
            discount_description=policy.description,
        )
        self._orders.append(order)
        return order

    # ----------------------------------------------- chuyển trạng thái (State)
    def ship(self, order_id: str) -> Order:
        order = self.get(order_id)
        order.ship()
        return order

    def complete(self, order_id: str) -> Order:
        order = self.get(order_id)
        order.complete()
        for listener in self._listeners:
            listener.order_completed(order)
        return order

    def cancel(self, order_id: str) -> Order:
        order = self.get(order_id)
        order.cancel()
        for listener in self._listeners:
            listener.order_cancelled(order)
        return order
