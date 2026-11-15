"""Dịch vụ hội viên E-Book: đăng ký gói, kích hoạt khi admin xác nhận thanh toán, cấp link Drive."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping

from ..models import Customer, EBook, EBookVault, Order, OrderType
from .customers import CustomerService
from .events import OrderListener
from .inventory import InventoryService
from .orders import OrderService


@dataclass(frozen=True)
class DriveAccess:
    """Kết quả mở khóa: link thư mục tổng và link từng E-Book."""

    folder_url: str
    ebook_links: dict[str, str] = field(default_factory=dict)


class MembershipService(OrderListener):
    PAYMENT_METHOD = "Chuyển khoản ngân hàng"

    def __init__(
        self,
        vault: EBookVault,
        customers: CustomerService,
        orders: OrderService,
        inventory: InventoryService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._vault = vault
        self._customers = customers
        self._orders = orders
        self._inventory = inventory
        self._clock = clock

    @property
    def vault(self) -> EBookVault:
        return self._vault

    def update_vault(self, changes: Mapping[str, Any]) -> EBookVault:
        # Tạo đối tượng mới từ dữ liệu đã gộp: dữ liệu sai sẽ báo lỗi mà không sửa dở kho hiện tại.
        self._vault = EBookVault.from_dict({**self._vault.to_dict(), **changes})
        return self._vault

    def ebooks(self) -> list[EBook]:
        return self._inventory.ebooks()

    # ------------------------------------------------------- quyền truy cập
    def has_access(self, customer: Customer | None) -> bool:
        return self._vault.can_access(customer, self._clock())

    def drive_access(self, customer: Customer | None) -> DriveAccess:
        """Báo AccessDeniedError nếu khách không có gói còn hạn."""
        now = self._clock()
        folder = self._vault.open_folder(customer, now)
        links = {e.id: self._vault.open_ebook(e, customer, now) for e in self.ebooks() if e.has_drive_link}
        return DriveAccess(folder, links)

    def admin_drive_access(self) -> DriveAccess:
        return DriveAccess(self._vault.folder_url, {e.id: e.drive_link for e in self.ebooks() if e.has_drive_link})

    def active_members(self) -> list[Customer]:
        now = self._clock()
        return [c for c in self._customers.all() if c.membership.is_valid(now)]

    # ------------------------------------------------------------ đăng ký gói
    def pending_request(self, customer: Customer) -> Order | None:
        return next(
            (o for o in self._orders.by_customer(customer.id) if o.order_type is OrderType.MEMBERSHIP and o.is_pending),
            None,
        )

    def request(self, customer: Customer) -> Order:
        """Khách báo đã chuyển khoản: tạo đơn chờ admin xác nhận (không tạo trùng)."""
        existing = self.pending_request(customer)
        if existing is not None:
            return existing
        return self._orders.record_membership(customer, self._vault.create_plan(), self.PAYMENT_METHOD)

    def grant(self, customer_id: str) -> Customer:
        """Quản trị viên tặng / gia hạn gói miễn phí."""
        customer = self._customers.get(customer_id)
        customer.membership.renew(days=self._vault.duration_days, fee=0, payment_ref="ADMIN-GRANT", now=self._clock())
        return customer

    def revoke(self, customer_id: str) -> Customer:
        customer = self._customers.get(customer_id)
        customer.membership.revoke(self._clock())
        return customer

    # ------------------------------------------------------- OrderListener
    def order_completed(self, order: Order) -> None:
        if order.order_type is not OrderType.MEMBERSHIP:
            return
        customer = self._customers.find(order.customer_id)
        if customer is not None:
            customer.membership.renew(
                days=self._vault.duration_days, fee=order.final_total, payment_ref=order.id, now=self._clock()
            )

    def order_cancelled(self, order: Order) -> None:
        """Đơn hội viên bị hủy thì không kích hoạt gì."""
