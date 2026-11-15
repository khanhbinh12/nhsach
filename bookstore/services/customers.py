"""Dịch vụ quản lý khách hàng."""

from __future__ import annotations

from typing import Iterable

from ..exceptions import NotFoundError, ValidationError
from ..models import DEFAULT_IDS, Customer, CustomerFactory, IdGenerator, Order, VIPCustomer, VIPTier
from .events import OrderListener


class CustomerService(OrderListener):
    """Quản lý khách hàng; lắng nghe sự kiện xác nhận đơn để cộng chi tiêu và điểm."""

    def __init__(self, customers: Iterable[Customer] = (), ids: IdGenerator = DEFAULT_IDS) -> None:
        self._ids = ids
        self._customers: dict[str, Customer] = {}
        for customer in customers:
            self.add(customer)

    def find(self, customer_id: str | None) -> Customer | None:
        return self._customers.get(customer_id or "")

    def get(self, customer_id: str) -> Customer:
        customer = self.find(customer_id)
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng '{customer_id}'")
        return customer

    def new_id(self) -> str:
        """Mã khách hàng chưa dùng."""
        return self._ids.new_id(Customer.ID_PREFIX, self._customers.__contains__)

    def find_by_identifier(self, identifier: str) -> Customer | None:
        """Tìm theo số điện thoại hoặc email."""
        return next((c for c in self._customers.values() if c.matches(identifier)), None)

    def all(self) -> list[Customer]:
        return list(self._customers.values())

    def search(self, keyword: str = "") -> list[Customer]:
        key = keyword.strip().lower()
        if not key:
            return self.all()
        return [c for c in self._customers.values() if key in f"{c.id} {c.name} {c.phone} {c.email}".lower()]

    def __len__(self) -> int:
        return len(self._customers)

    def ensure_unique(self, customer: Customer) -> None:
        """Báo lỗi nếu mã, số điện thoại hoặc email đã được dùng."""
        if customer.id in self._customers:
            raise ValidationError(f"Mã khách hàng '{customer.id}' đã tồn tại")
        if self.find_by_identifier(customer.phone):
            raise ValidationError(f"Số điện thoại {customer.phone} đã được đăng ký")
        if customer.email and self.find_by_identifier(customer.email):
            raise ValidationError(f"Email {customer.email} đã được đăng ký")

    def add(self, customer: Customer) -> Customer:
        self.ensure_unique(customer)
        self._customers[customer.id] = customer
        return customer

    def register(
        self,
        *,
        name: str,
        phone: str,
        email: str = "",
        is_vip: bool = False,
        tier: VIPTier | str = VIPTier.BRONZE,
        customer_id: str | None = None,
    ) -> Customer:
        customer = CustomerFactory.create(
            name=name, phone=phone, email=email, is_vip=is_vip, tier=tier, customer_id=customer_id or self.new_id()
        )
        return self.add(customer)

    def promote_to_vip(self, customer_id: str, tier: VIPTier | str = VIPTier.BRONZE) -> Customer:
        """Nâng khách thường lên VIP: tạo đối tượng VIPCustomer mới giữ nguyên lịch sử."""
        customer = self.get(customer_id)
        if customer.is_vip:
            raise ValidationError(f"{customer.name} đã là khách VIP")
        vip = VIPCustomer.from_dict({**customer.to_dict(), "type": VIPCustomer.TYPE_CODE, "base_tier": VIPTier(tier)})
        self._customers[customer_id] = vip
        return vip

    # ------------------------------------------------------- OrderListener
    def order_completed(self, order: Order) -> None:
        customer = self.find(order.customer_id)
        if customer is not None:
            customer.record_purchase(order.final_total)

    def order_cancelled(self, order: Order) -> None:
        """Đơn hủy chưa từng được cộng chi tiêu nên không cần hoàn tác."""
