"""Hội viên E-Book và Kho Google Drive được bảo vệ."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Mapping

from ..exceptions import AccessDeniedError, NotFoundError, ValidationError
from .product import EBook, MembershipPlan
from .tracking import Trackable
from .validators import optional_text, require_text, to_float, to_int

if TYPE_CHECKING:
    from .person import Customer

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_datetime(value: object) -> datetime | None:
    text = optional_text(value)
    if not text:
        return None
    try:
        return datetime.strptime(text[:19], DATE_FORMAT)
    except ValueError:
        raise ValidationError(f"Ngày giờ không hợp lệ: '{text}'") from None


def _format_datetime(value: datetime | None) -> str:
    return value.strftime(DATE_FORMAT) if value else ""


class EBookMembership(Trackable):
    """Thời hạn hội viên của một khách hàng.

    Quan hệ Composition: mỗi ``Customer`` *có một* ``EBookMembership``. Trạng thái chỉ thay đổi
    qua ``renew()`` / ``revoke()`` nên không thể bị gán sai từ bên ngoài.
    Tham số ``now`` cho phép kiểm thử với thời điểm giả định.
    """

    def __init__(
        self,
        *,
        activated_at: datetime | None = None,
        expires_at: datetime | None = None,
        total_paid: float = 0.0,
        payment_ref: str = "",
        revoked: bool = False,
    ) -> None:
        self._activated_at = activated_at
        self._expires_at = expires_at
        self._total_paid = float(total_paid)
        self._payment_ref = payment_ref
        self._revoked = bool(revoked)

    @property
    def activated_at(self) -> datetime | None:
        return self._activated_at

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def total_paid(self) -> float:
        return self._total_paid

    @property
    def payment_ref(self) -> str:
        return self._payment_ref

    def is_valid(self, now: datetime | None = None) -> bool:
        if self._revoked or self._expires_at is None:
            return False
        return (now or datetime.now()) <= self._expires_at

    def days_remaining(self, now: datetime | None = None) -> int:
        now = now or datetime.now()
        if not self.is_valid(now):
            return 0
        return max(0, math.ceil((self._expires_at - now).total_seconds() / 86_400))

    def renew(self, *, days: int, fee: float, payment_ref: str, now: datetime | None = None) -> None:
        """Kích hoạt hoặc gia hạn. Nếu gói còn hạn, thời hạn mới được cộng nối tiếp."""
        if days <= 0:
            raise ValidationError("Số ngày gia hạn phải lớn hơn 0")
        now = now or datetime.now()
        if self.is_valid(now):
            start = self._expires_at
        else:
            start = now
            self._activated_at = now
        self._expires_at = start + timedelta(days=days)
        self._total_paid += float(fee)
        self._payment_ref = payment_ref
        self._revoked = False

    def revoke(self, now: datetime | None = None) -> None:
        if not self.is_valid(now):
            raise ValidationError("Khách hàng không có gói hội viên đang hiệu lực để thu hồi")
        self._revoked = True

    def status_label(self, now: datetime | None = None) -> str:
        now = now or datetime.now()
        if self.is_valid(now):
            return f"Còn {self.days_remaining(now)} ngày (đến {self._expires_at:%d/%m/%Y})"
        if self._revoked:
            return "Đã thu hồi"
        if self._expires_at:
            return f"Hết hạn {self._expires_at:%d/%m/%Y}"
        return "Chưa đăng ký"

    def to_dict(self) -> dict[str, Any]:
        return {
            "activated_at": _format_datetime(self._activated_at),
            "expires_at": _format_datetime(self._expires_at),
            "total_paid": self._total_paid,
            "payment_ref": self._payment_ref,
            "revoked": self._revoked,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EBookMembership":
        return cls(
            activated_at=_parse_datetime(data.get("activated_at")),
            expires_at=_parse_datetime(data.get("expires_at")),
            total_paid=to_float(data.get("total_paid", 0) or 0, "Tổng phí đã trả"),
            payment_ref=optional_text(data.get("payment_ref")),
            revoked=bool(data.get("revoked", False)),
        )


class EBookVault:
    """Kho Google Drive dành cho hội viên.

    Đóng gói quyền truy cập: link thư mục / link từng E-Book chỉ được trả về qua
    ``open_folder()`` / ``open_ebook()`` sau khi kiểm tra khách còn hạn hội viên.
    """

    def __init__(
        self,
        *,
        title: str = "Kho Thư Viện E-Book Google Drive",
        folder_url: str = "https://drive.google.com/drive/folders/1TriTriBookstoreEBookVault2026",
        membership_fee: float | str = 100_000,
        duration_days: int | str = 365,
        description: str = "Truy cập toàn bộ thư mục E-Book PDF/EPUB và sách mới cập nhật liên tục.",
        bank_info: str = "Vietcombank · STK 0123 456 789 · NHA SACH TRI TRI (dữ liệu mẫu)",
    ) -> None:
        self.title = title
        self.folder_url = folder_url
        self.membership_fee = membership_fee
        self.duration_days = duration_days
        self.description = description
        self.bank_info = bank_info

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = require_text(value, "Tên kho")

    @property
    def folder_url(self) -> str:
        return self._folder_url

    @folder_url.setter
    def folder_url(self, value: str) -> None:
        url = require_text(value, "Link thư mục Google Drive")
        if not url.startswith(("http://", "https://")):
            raise ValidationError("Link thư mục phải bắt đầu bằng http:// hoặc https://")
        self._folder_url = url

    @property
    def membership_fee(self) -> float:
        return self._membership_fee

    @membership_fee.setter
    def membership_fee(self, value: float | str) -> None:
        self._membership_fee = to_float(value, "Phí hội viên")

    @property
    def duration_days(self) -> int:
        return self._duration_days

    @duration_days.setter
    def duration_days(self, value: int | str) -> None:
        self._duration_days = to_int(value, "Thời hạn hội viên (ngày)", minimum=1)

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = optional_text(value)

    @property
    def bank_info(self) -> str:
        """Thông tin chuyển khoản hiển thị khi khách mua gói hội viên."""
        return self._bank_info

    @bank_info.setter
    def bank_info(self, value: str) -> None:
        self._bank_info = require_text(value, "Thông tin chuyển khoản")

    # --------------------------------------------------- kiểm soát truy cập
    def can_access(self, customer: "Customer | None", now: datetime | None = None) -> bool:
        return customer is not None and customer.membership.is_valid(now)

    def _ensure_access(self, customer: "Customer | None", now: datetime | None) -> None:
        if not self.can_access(customer, now):
            raise AccessDeniedError("Cần gói hội viên E-Book còn hiệu lực để xem link Drive")

    def open_folder(self, customer: "Customer | None", now: datetime | None = None) -> str:
        self._ensure_access(customer, now)
        return self._folder_url

    def open_ebook(self, ebook: EBook, customer: "Customer | None", now: datetime | None = None) -> str:
        self._ensure_access(customer, now)
        if not ebook.has_drive_link:
            raise NotFoundError(f"E-Book '{ebook.title}' chưa được cấu hình link Drive")
        return ebook.drive_link

    def create_plan(self) -> MembershipPlan:
        return MembershipPlan(
            title=f"Gói Hội Viên Kho E-Book ({self._duration_days} ngày)",
            price=self._membership_fee,
            duration_days=self._duration_days,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self._title,
            "folder_url": self._folder_url,
            "membership_fee": self._membership_fee,
            "duration_days": self._duration_days,
            "description": self._description,
            "bank_info": self._bank_info,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EBookVault":
        defaults = cls().to_dict()
        merged = {**defaults, **{k: v for k, v in data.items() if k in defaults}}
        return cls(**merged)
