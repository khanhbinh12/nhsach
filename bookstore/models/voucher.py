"""Mã giảm giá khách tự nhập (voucher).

    DiscountPolicy (trừu tượng)
    └── Voucher (trừu tượng): mã, đơn tối thiểu, hạn dùng, giới hạn lượt
        ├── PercentVoucher      – giảm theo %
        └── FixedAmountVoucher  – giảm số tiền cố định

Thêm loại voucher mới chỉ cần viết lớp con với ``KIND`` riêng – không sửa code cũ (Open/Closed).
"""

from __future__ import annotations

import re
from abc import abstractmethod
from datetime import date
from typing import TYPE_CHECKING, Any, ClassVar, Mapping

from ..exceptions import ValidationError
from .discount import DiscountPolicy
from .tracking import Trackable
from .validators import optional_text, require_text, to_float, to_int

if TYPE_CHECKING:
    from .person import Customer


def _money(amount: float) -> str:
    return f"{amount:,.0f}đ".replace(",", ".")


class Voucher(Trackable, DiscountPolicy):
    KIND: ClassVar[str] = ""
    KIND_LABEL: ClassVar[str] = ""
    CODE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Z0-9_-]{3,20}$")
    _registry: ClassVar[dict[str, type["Voucher"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.KIND:
            Voucher._registry[cls.KIND] = cls

    def __init__(
        self,
        *,
        code: str,
        min_subtotal: float | str = 0,
        valid_until: date | str | None = None,
        usage_limit: int | str | None = None,
        used_count: int | str = 0,
        active: bool = True,
    ) -> None:
        normalized = require_text(code, "Mã giảm giá").upper()
        if not self.CODE_PATTERN.match(normalized):
            raise ValidationError("Mã giảm giá gồm 3–20 ký tự: chữ cái không dấu, số, '-' hoặc '_'")
        self._code = normalized
        self._min_subtotal = to_float(min_subtotal or 0, "Đơn tối thiểu")
        self._valid_until = self._parse_date(valid_until)
        limit = optional_text(usage_limit)
        self._usage_limit = to_int(limit, "Số lượt dùng tối đa", minimum=1) if limit else None
        self._used_count = to_int(used_count or 0, "Số lượt đã dùng")
        self.active = active

    @staticmethod
    def _parse_date(value: date | str | None) -> date | None:
        if isinstance(value, date) or value is None:
            return value
        text = optional_text(value)
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            raise ValidationError(f"Ngày hết hạn không hợp lệ: '{text}'") from None

    # ------------------------------------------------------- thuộc tính
    @property
    def code(self) -> str:
        return self._code

    @property
    def min_subtotal(self) -> float:
        return self._min_subtotal

    @property
    def valid_until(self) -> date | None:
        return self._valid_until

    @property
    def usage_limit(self) -> int | None:
        return self._usage_limit

    @property
    def used_count(self) -> int:
        return self._used_count

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = bool(value)

    @property
    def remaining_uses(self) -> int | None:
        return None if self._usage_limit is None else max(0, self._usage_limit - self._used_count)

    @property
    def description(self) -> str:
        condition = f" cho đơn từ {_money(self._min_subtotal)}" if self._min_subtotal else ""
        return f"Mã {self._code}: {self.value_label}{condition}"

    # ------------------------------------------------------- đa hình
    @property
    @abstractmethod
    def value_label(self) -> str:
        """Mức giảm hiển thị, ví dụ '-10%' hoặc '-30.000đ'."""

    @abstractmethod
    def _raw_discount(self, subtotal: float) -> float:
        """Số tiền giảm trước khi áp giới hạn – mỗi loại voucher tự tính."""

    def calculate(self, subtotal: float, customer: "Customer | None", quantity: int) -> float:
        if subtotal < self._min_subtotal:
            return 0.0
        return float(min(subtotal, round(self._raw_discount(subtotal))))

    # ------------------------------------------------------- kiểm tra & sử dụng
    def check_usable(self, subtotal: float, today: date) -> None:
        """Báo lỗi kèm lý do cụ thể nếu mã không dùng được cho đơn này."""
        if not self._active:
            raise ValidationError(f"Mã {self._code} đã ngừng áp dụng")
        if self._valid_until is not None and today > self._valid_until:
            raise ValidationError(f"Mã {self._code} đã hết hạn từ {self._valid_until:%d/%m/%Y}")
        if self.remaining_uses == 0:
            raise ValidationError(f"Mã {self._code} đã hết lượt sử dụng")
        if subtotal < self._min_subtotal:
            raise ValidationError(f"Mã {self._code} chỉ áp dụng cho đơn từ {_money(self._min_subtotal)}")

    def use(self) -> None:
        if self.remaining_uses == 0:
            raise ValidationError(f"Mã {self._code} đã hết lượt sử dụng")
        self._used_count += 1

    def release(self) -> None:
        """Hoàn lại một lượt khi đơn dùng mã bị hủy."""
        self._used_count = max(0, self._used_count - 1)

    # ------------------------------------------------------- lưu trữ
    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.KIND,
            "code": self._code,
            "min_subtotal": self._min_subtotal,
            "valid_until": self._valid_until.isoformat() if self._valid_until else "",
            "usage_limit": self._usage_limit,
            "used_count": self._used_count,
            "active": self._active,
            **self._extra_dict(),
        }

    @abstractmethod
    def _extra_dict(self) -> dict[str, Any]:
        """Trường riêng của từng loại voucher."""

    @staticmethod
    def _base_kwargs(data: Mapping[str, Any]) -> dict[str, Any]:
        return {key: data.get(key) for key in ("code", "min_subtotal", "valid_until", "usage_limit")} | {
            "used_count": data.get("used_count", 0),
            "active": bool(data.get("active", True)),
        }

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Voucher":
        """Khôi phục voucher từ dữ liệu đã lưu."""

    @classmethod
    @abstractmethod
    def from_form(cls, data: Mapping[str, Any]) -> "Voucher":
        """Tạo voucher từ form quản trị (giá trị nhập theo cách thân thiện với người dùng)."""

    @staticmethod
    def kinds() -> dict[str, str]:
        return {kind: cls.KIND_LABEL for kind, cls in Voucher._registry.items()}

    @staticmethod
    def restore(data: Mapping[str, Any]) -> "Voucher":
        return Voucher._class_for(data.get("kind")).from_dict(data)

    @staticmethod
    def create(data: Mapping[str, Any]) -> "Voucher":
        return Voucher._class_for(data.get("kind")).from_form(data)

    @staticmethod
    def _class_for(kind: Any) -> type["Voucher"]:
        voucher_cls = Voucher._registry.get(optional_text(kind).upper())
        if voucher_cls is None:
            raise ValidationError(f"Loại mã giảm giá không hỗ trợ: '{kind}'")
        return voucher_cls


class PercentVoucher(Voucher):
    """Giảm theo phần trăm giá trị đơn."""

    KIND = "PERCENT"
    KIND_LABEL = "Giảm theo %"

    def __init__(self, *, rate: float | str, **base: Any) -> None:
        super().__init__(**base)
        rate = to_float(rate, "Tỷ lệ giảm")
        if not 0 < rate <= 0.5:
            raise ValidationError("Tỷ lệ giảm phải từ 1% đến 50%")
        self._rate = rate

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def value_label(self) -> str:
        return f"-{self._rate:.0%}"

    def _raw_discount(self, subtotal: float) -> float:
        return subtotal * self._rate

    def _extra_dict(self) -> dict[str, Any]:
        return {"rate": self._rate}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PercentVoucher":
        return cls(rate=data.get("rate"), **cls._base_kwargs(data))

    @classmethod
    def from_form(cls, data: Mapping[str, Any]) -> "PercentVoucher":
        return cls(rate=to_float(data.get("value"), "Mức giảm (%)") / 100, **cls._base_kwargs(data))


class FixedAmountVoucher(Voucher):
    """Giảm một số tiền cố định."""

    KIND = "FIXED"
    KIND_LABEL = "Giảm số tiền"

    def __init__(self, *, amount: float | str, **base: Any) -> None:
        super().__init__(**base)
        self._amount = to_float(amount, "Số tiền giảm", minimum=1000)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def value_label(self) -> str:
        return f"-{_money(self._amount)}"

    def _raw_discount(self, subtotal: float) -> float:
        return self._amount

    def _extra_dict(self) -> dict[str, Any]:
        return {"amount": self._amount}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FixedAmountVoucher":
        return cls(amount=data.get("amount"), **cls._base_kwargs(data))

    @classmethod
    def from_form(cls, data: Mapping[str, Any]) -> "FixedAmountVoucher":
        return cls(amount=data.get("value"), **cls._base_kwargs(data))
