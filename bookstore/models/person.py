"""Cây kế thừa con người: Person (trừu tượng) → Customer → VIPCustomer."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, ClassVar, Mapping

from ..exceptions import ValidationError
from .enums import VIPTier
from .identifiers import DEFAULT_IDS
from .membership import EBookMembership
from .tracking import Trackable
from .validators import optional_text, require_text, to_float, to_int


class Person(Trackable, ABC):
    """Lớp trừu tượng: thông tin định danh và liên hệ của một người."""

    PHONE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^(0|\+84)\d{9,10}$")
    EMAIL_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, *, person_id: str, name: str, phone: str, email: str = "") -> None:
        self._id = require_text(person_id, "Mã định danh")
        self.name = name
        self.phone = phone
        self.email = email

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = require_text(value, "Họ tên")

    @property
    def phone(self) -> str:
        return self._phone

    @phone.setter
    def phone(self, value: str) -> None:
        phone = re.sub(r"[\s.\-]", "", require_text(value, "Số điện thoại"))
        if not self.PHONE_PATTERN.match(phone):
            raise ValidationError(f"Số điện thoại không hợp lệ: '{value}' (cần 10–11 chữ số, bắt đầu bằng 0)")
        self._phone = phone

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        email = optional_text(value).lower()
        if email and not self.EMAIL_PATTERN.match(email):
            raise ValidationError(f"Email không hợp lệ: '{value}'")
        self._email = email

    @property
    @abstractmethod
    def role(self) -> str:
        """Vai trò của người này trong hệ thống."""

    def matches(self, identifier: str) -> bool:
        """Đúng nếu ``identifier`` trùng số điện thoại hoặc email."""
        key = re.sub(r"[\s.\-]", "", optional_text(identifier)).lower()
        if not key:
            return False
        return key == self._phone or (bool(self._email) and optional_text(identifier).lower() == self._email)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self._id, "name": self._name, "phone": self._phone, "email": self._email}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id!r}, name={self._name!r})"


class Customer(Person):
    """Khách hàng thường: tích điểm 1 điểm / 10.000đ, không chiết khấu."""

    ID_PREFIX: ClassVar[str] = "KH"
    TYPE_CODE: ClassVar[str] = "STANDARD"
    POINT_UNIT: ClassVar[float] = 10_000
    POINTS_MULTIPLIER: ClassVar[int] = 1

    def __init__(
        self,
        *,
        customer_id: str | None = None,
        name: str,
        phone: str,
        email: str = "",
        loyalty_points: int | str = 0,
        total_spent: float | str = 0.0,
        joined_date: str | None = None,
        membership: EBookMembership | None = None,
    ) -> None:
        super().__init__(
            person_id=customer_id or DEFAULT_IDS.new_id(self.ID_PREFIX), name=name, phone=phone, email=email
        )
        self._loyalty_points = to_int(loyalty_points, "Điểm tích lũy")
        self._total_spent = to_float(total_spent, "Tổng chi tiêu")
        self._joined_date = optional_text(joined_date) or date.today().isoformat()
        self._membership = membership or EBookMembership()

    @property
    def role(self) -> str:
        return "Khách hàng thường"

    @property
    def tier(self) -> VIPTier:
        return VIPTier.STANDARD

    @property
    def discount_rate(self) -> float:
        return 0.0

    @property
    def is_vip(self) -> bool:
        return False

    @property
    def loyalty_points(self) -> int:
        return self._loyalty_points

    @property
    def total_spent(self) -> float:
        return self._total_spent

    @property
    def joined_date(self) -> str:
        return self._joined_date

    @property
    def membership(self) -> EBookMembership:
        return self._membership

    # Gói hội viên là đối tượng con (Composition): nó thay đổi thì khách hàng cũng phải được lưu lại.
    @property
    def is_dirty(self) -> bool:
        return super().is_dirty or self._membership.is_dirty

    def mark_clean(self) -> None:
        super().mark_clean()
        self._membership.mark_clean()

    def record_purchase(self, amount: float) -> int:
        """Template Method: cộng chi tiêu và điểm; cách tính điểm do ``_points_for`` quyết định."""
        if amount <= 0:
            return 0
        self._total_spent += amount
        earned = self._points_for(amount)
        self._loyalty_points += earned
        return earned

    def _points_for(self, amount: float) -> int:
        return int(amount // self.POINT_UNIT) * self.POINTS_MULTIPLIER

    def redeem_points(self, points: int) -> None:
        if points <= 0 or points > self._loyalty_points:
            raise ValidationError(f"Không thể đổi {points} điểm (hiện có {self._loyalty_points})")
        self._loyalty_points -= points

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            type=self.TYPE_CODE,
            loyalty_points=self._loyalty_points,
            total_spent=self._total_spent,
            joined_date=self._joined_date,
            membership=self._membership.to_dict(),
        )
        return data

    @classmethod
    def _extra_kwargs(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        """Hook cho lớp con bổ sung tham số riêng khi khôi phục từ dữ liệu."""
        return {}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Customer":
        return cls(
            customer_id=data.get("id"),
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email", ""),
            loyalty_points=data.get("loyalty_points", 0),
            total_spent=data.get("total_spent", 0),
            joined_date=data.get("joined_date"),
            membership=EBookMembership.from_dict(data.get("membership") or {}),
            **cls._extra_kwargs(data),
        )


class VIPCustomer(Customer):
    """Khách VIP: điểm x2, chiết khấu theo hạng; hạng tự nâng theo tổng chi tiêu."""

    TYPE_CODE = "VIP"
    POINTS_MULTIPLIER = 2
    SPENDING_TIERS: ClassVar[tuple[tuple[float, VIPTier], ...]] = (
        (15_000_000, VIPTier.PLATINUM),
        (8_000_000, VIPTier.GOLD),
        (3_000_000, VIPTier.SILVER),
    )
    DISCOUNT_RATES: ClassVar[dict[VIPTier, float]] = {
        VIPTier.BRONZE: 0.05,
        VIPTier.SILVER: 0.10,
        VIPTier.GOLD: 0.15,
        VIPTier.PLATINUM: 0.20,
    }

    def __init__(self, *, base_tier: VIPTier | str = VIPTier.BRONZE, **customer_kwargs: Any) -> None:
        super().__init__(**customer_kwargs)
        try:
            tier = VIPTier(base_tier)
        except ValueError:
            raise ValidationError(f"Hạng VIP không hợp lệ: '{base_tier}'") from None
        self._base_tier = VIPTier.BRONZE if tier is VIPTier.STANDARD else tier

    @property
    def role(self) -> str:
        return "Khách hàng VIP"

    @property
    def base_tier(self) -> VIPTier:
        """Hạng được cấp trực tiếp (hạng tối thiểu)."""
        return self._base_tier

    @property
    def tier(self) -> VIPTier:
        earned = next((tier for limit, tier in self.SPENDING_TIERS if self._total_spent >= limit), VIPTier.BRONZE)
        return max(earned, self._base_tier, key=lambda t: t.rank)

    @property
    def discount_rate(self) -> float:
        return self.DISCOUNT_RATES[self.tier]

    @property
    def is_vip(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["base_tier"] = self._base_tier.value
        return data

    @classmethod
    def _extra_kwargs(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        return {"base_tier": data.get("base_tier", VIPTier.BRONZE.value)}


class CustomerFactory:
    """Tạo đúng lớp khách hàng theo loại (STANDARD / VIP)."""

    _types: ClassVar[dict[str, type[Customer]]] = {cls.TYPE_CODE: cls for cls in (Customer, VIPCustomer)}

    @classmethod
    def create(
        cls,
        *,
        name: str,
        phone: str,
        email: str = "",
        is_vip: bool = False,
        tier: VIPTier | str = VIPTier.BRONZE,
        customer_id: str | None = None,
    ) -> Customer:
        if is_vip:
            return VIPCustomer(customer_id=customer_id, name=name, phone=phone, email=email, base_tier=tier)
        return Customer(customer_id=customer_id, name=name, phone=phone, email=email)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Customer:
        type_code = optional_text(data.get("type")).upper() or Customer.TYPE_CODE
        customer_cls = cls._types.get(type_code)
        if customer_cls is None:
            raise ValidationError(f"Loại khách hàng không hỗ trợ: '{type_code}'")
        return customer_cls.from_dict(data)
