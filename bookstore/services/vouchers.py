"""Dịch vụ mã giảm giá; lắng nghe sự kiện hủy đơn để hoàn lại lượt dùng mã."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Mapping

from ..exceptions import NotFoundError, ValidationError
from ..models import Order, Voucher
from ..models.validators import optional_text
from .events import OrderListener


class VoucherService(OrderListener):
    def __init__(self, vouchers: Iterable[Voucher] = (), clock: Callable[[], datetime] = datetime.now) -> None:
        self._vouchers: dict[str, Voucher] = {}
        self._clock = clock
        for voucher in vouchers:
            self.add(voucher)

    def all(self) -> list[Voucher]:
        return list(self._vouchers.values())

    def find(self, code: str | None) -> Voucher | None:
        return self._vouchers.get(optional_text(code).upper())

    def get(self, code: str) -> Voucher:
        voucher = self.find(code)
        if voucher is None:
            raise NotFoundError(f"Không tìm thấy mã giảm giá '{code}'")
        return voucher

    def add(self, voucher: Voucher) -> Voucher:
        if voucher.code in self._vouchers:
            raise ValidationError(f"Mã {voucher.code} đã tồn tại")
        self._vouchers[voucher.code] = voucher
        return voucher

    def create(self, form: Mapping[str, Any]) -> Voucher:
        return self.add(Voucher.create(form))  # đa hình: đúng lớp con theo 'kind'

    def set_active(self, code: str, active: bool) -> Voucher:
        voucher = self.get(code)
        voucher.active = active
        return voucher

    def remove(self, code: str) -> Voucher:
        voucher = self.get(code)
        del self._vouchers[voucher.code]
        return voucher

    def validate(self, code: str, subtotal: float) -> Voucher:
        """Trả về voucher nếu dùng được cho đơn có giá trị ``subtotal``; ngược lại báo lý do."""
        voucher = self.find(code)
        if voucher is None:
            raise ValidationError(f"Mã giảm giá '{optional_text(code).upper()}' không tồn tại")
        voucher.check_usable(subtotal, self._clock().date())
        return voucher

    # ------------------------------------------------------- OrderListener
    def order_completed(self, order: Order) -> None:
        """Lượt dùng mã đã được tính lúc đặt đơn."""

    def order_cancelled(self, order: Order) -> None:
        voucher = self.find(order.discount_code)
        if voucher is not None:
            voucher.release()
