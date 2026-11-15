"""Giỏ hàng và hóa đơn.

Hóa đơn lưu *bản chụp* (snapshot) giá, giảm giá và phí ship tại thời điểm thanh toán,
nên sửa giá sách hay khách lên hạng VIP về sau không làm thay đổi hóa đơn cũ.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Iterator, Mapping

from ..exceptions import NotFoundError, OutOfStockError, ValidationError
from .enums import OrderAction, OrderStatus, OrderType, ProductFormat
from .identifiers import DEFAULT_IDS
from .order_state import OrderState
from .product import Product
from .tracking import Trackable
from .validators import optional_text, to_int


@dataclass(frozen=True)
class OrderLine:
    """Một dòng hóa đơn – bất biến (frozen) sau khi tạo."""

    product_id: str
    title: str
    category: str
    format: ProductFormat
    unit_price: float
    quantity: int
    shipping_fee: float

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity

    @classmethod
    def from_product(cls, product: Product, quantity: int) -> "OrderLine":
        return cls(
            product_id=product.id,
            title=product.title,
            category=product.category,
            format=product.format,
            unit_price=product.price,
            quantity=quantity,
            shipping_fee=product.shipping_fee(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "title": self.title,
            "category": self.category,
            "format": self.format.value,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "shipping_fee": self.shipping_fee,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OrderLine":
        return cls(
            product_id=str(data["product_id"]),
            title=str(data["title"]),
            category=str(data.get("category", "")),
            format=ProductFormat(data["format"]),
            unit_price=float(data["unit_price"]),
            quantity=int(data["quantity"]),
            shipping_fee=float(data.get("shipping_fee", 0)),
        )


@dataclass(frozen=True)
class OrderQuote:
    """Bảng tính tiền tạm (xem trước khi thanh toán)."""

    subtotal: float
    discount_amount: float
    shipping_fee: float
    policy_code: str
    policy_description: str
    voucher_code: str = ""

    @property
    def total(self) -> float:
        return max(0.0, self.subtotal - self.discount_amount + self.shipping_fee)

    @property
    def voucher_applied(self) -> bool:
        return bool(self.voucher_code) and self.voucher_code == self.policy_code


class Cart:
    """Giỏ hàng: gộp sản phẩm trùng và kiểm tra tồn kho ngay khi thêm."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[Product, int]] = {}

    def add(self, product: Product, quantity: int | str = 1) -> None:
        if not product.purchasable:
            raise ValidationError(f"'{product.title}' không bán lẻ (thuộc Kho E-Book dành cho hội viên)")
        qty = to_int(quantity, "Số lượng", minimum=1)
        new_quantity = self.quantity_of(product.id) + qty
        if not product.can_supply(new_quantity):
            raise OutOfStockError(f"'{product.title}' không đủ hàng (còn {product.stock_label()}, cần {new_quantity})")
        self._entries[product.id] = (product, new_quantity)

    def set_quantity(self, product_id: str, quantity: int) -> None:
        if product_id not in self._entries:
            raise NotFoundError("Sản phẩm không có trong giỏ")
        if quantity <= 0:
            self.remove(product_id)
            return
        product, _ = self._entries[product_id]
        if not product.can_supply(quantity):
            raise OutOfStockError(f"'{product.title}' chỉ còn {product.stock_label()}")
        self._entries[product_id] = (product, quantity)

    def remove(self, product_id: str) -> None:
        self._entries.pop(product_id, None)

    def clear(self) -> None:
        self._entries.clear()

    def quantity_of(self, product_id: str) -> int:
        entry = self._entries.get(product_id)
        return entry[1] if entry else 0

    def items(self) -> list[tuple[Product, int]]:
        return list(self._entries.values())

    def is_empty(self) -> bool:
        return not self._entries

    def total_quantity(self) -> int:
        return sum(qty for _, qty in self._entries.values())

    def subtotal(self) -> float:
        return sum(product.price * qty for product, qty in self._entries.values())

    def to_lines(self) -> list[OrderLine]:
        return [OrderLine.from_product(product, qty) for product, qty in self._entries.values()]

    def __iter__(self) -> Iterator[tuple[Product, int]]:
        return iter(self.items())

    def __len__(self) -> int:
        return len(self._entries)


class Order(Trackable):
    """Đơn hàng – mọi số tiền được chốt tại thời điểm tạo; chỉ trạng thái được phép thay đổi.

    Trạng thái được ủy quyền cho đối tượng ``OrderState`` (State Pattern) – xem ``order_state.py``.
    """

    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        *,
        order_type: OrderType,
        lines: Iterable[OrderLine],
        payment_method: str,
        order_id: str | None = None,
        created_at: datetime | None = None,
        customer_id: str | None = None,
        customer_name: str = "Khách lẻ",
        contact_phone: str = "",
        discount_code: str = "NONE",
        discount_description: str = "",
        discount_amount: float = 0.0,
        shipping_fee: float = 0.0,
        shipping_address: str = "",
        status: OrderStatus = OrderStatus.PENDING,
    ) -> None:
        self._lines = tuple(lines)
        if not self._lines:
            raise ValidationError("Hóa đơn phải có ít nhất một sản phẩm")
        if discount_amount < 0 or shipping_fee < 0:
            raise ValidationError("Số tiền giảm giá / phí ship không được âm")
        self._created_at = created_at or datetime.now()
        self._id = optional_text(order_id) or DEFAULT_IDS.new_id(self.id_prefix(self._created_at))
        self._order_type = OrderType(order_type)
        self._customer_id = customer_id
        self._customer_name = optional_text(customer_name) or "Khách lẻ"
        self._contact_phone = optional_text(contact_phone)
        self._payment_method = optional_text(payment_method) or "Tiền mặt"
        self._discount_code = discount_code
        self._discount_description = discount_description
        self._discount_amount = float(discount_amount)
        self._shipping_fee = float(shipping_fee)
        self._shipping_address = optional_text(shipping_address)
        self._state: OrderState = OrderState.for_status(status)

    @staticmethod
    def id_prefix(created_at: datetime) -> str:
        """Mã đơn có ngày đặt để nhân viên dễ tra cứu, ví dụ HD-261115-7K3QX9."""
        return f"HD-{created_at:%y%m%d}"

    # ----------------------------------------------------- thuộc tính chỉ đọc
    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def order_type(self) -> OrderType:
        return self._order_type

    @property
    def customer_id(self) -> str | None:
        return self._customer_id

    @property
    def customer_name(self) -> str:
        return self._customer_name

    @property
    def contact_phone(self) -> str:
        return self._contact_phone

    @property
    def payment_method(self) -> str:
        return self._payment_method

    @property
    def discount_code(self) -> str:
        return self._discount_code

    @property
    def discount_description(self) -> str:
        return self._discount_description

    @property
    def discount_amount(self) -> float:
        return self._discount_amount

    @property
    def shipping_fee(self) -> float:
        return self._shipping_fee

    @property
    def shipping_address(self) -> str:
        return self._shipping_address

    @property
    def status(self) -> OrderStatus:
        return self._state.status

    @property
    def lines(self) -> tuple[OrderLine, ...]:
        return self._lines

    @property
    def is_pending(self) -> bool:
        return self.status is OrderStatus.PENDING

    @property
    def available_actions(self) -> tuple[OrderAction, ...]:
        return self._state.actions(self)

    @property
    def customer_can_cancel(self) -> bool:
        return self._state.customer_can_cancel

    @property
    def status_hint(self) -> str:
        return self._state.hint(self)

    # ------------------------------------- chuyển trạng thái (ủy quyền cho State)
    def ship(self) -> None:
        self._state = self._state.ship(self)

    def complete(self) -> None:
        self._state = self._state.complete(self)

    def cancel(self) -> None:
        self._state = self._state.cancel(self)

    # ------------------------------------------------------------ tính toán
    @property
    def total_quantity(self) -> int:
        return sum(line.quantity for line in self._lines)

    @property
    def subtotal(self) -> float:
        return sum(line.subtotal for line in self._lines)

    @property
    def final_total(self) -> float:
        return max(0.0, self.subtotal - self._discount_amount + self._shipping_fee)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "created_at": self._created_at.strftime(self.DATE_FORMAT),
            "order_type": self._order_type.value,
            "customer_id": self._customer_id,
            "customer_name": self._customer_name,
            "contact_phone": self._contact_phone,
            "payment_method": self._payment_method,
            "discount_code": self._discount_code,
            "discount_description": self._discount_description,
            "discount_amount": self._discount_amount,
            "shipping_fee": self._shipping_fee,
            "shipping_address": self._shipping_address,
            "status": self.status.value,
            "lines": [line.to_dict() for line in self._lines],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Order":
        return cls(
            order_id=data["id"],
            created_at=datetime.strptime(data["created_at"], cls.DATE_FORMAT),
            order_type=OrderType(data["order_type"]),
            customer_id=data.get("customer_id"),
            customer_name=data.get("customer_name", "Khách lẻ"),
            contact_phone=data.get("contact_phone", ""),
            payment_method=data.get("payment_method", "Tiền mặt"),
            discount_code=data.get("discount_code", "NONE"),
            discount_description=data.get("discount_description", ""),
            discount_amount=float(data.get("discount_amount", 0)),
            shipping_fee=float(data.get("shipping_fee", 0)),
            shipping_address=data.get("shipping_address", ""),
            status=OrderStatus(data.get("status", OrderStatus.PENDING.value)),
            lines=[OrderLine.from_dict(line) for line in data.get("lines", [])],
        )

    def __repr__(self) -> str:
        return f"Order(id={self._id!r}, total={self.final_total:.0f})"
