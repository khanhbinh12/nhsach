"""Chính sách giảm giá – Strategy Pattern.

    DiscountPolicy (trừu tượng)
    ├── NoDiscount
    ├── VIPDiscount
    └── ConditionalPercentDiscount (trừu tượng: giảm % khi đủ điều kiện)
        ├── SeasonalPromotion   – đơn từ 250.000đ giảm 12%
        └── BulkOrderDiscount   – mua từ 4 cuốn giảm 15%
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterable

from ..exceptions import ValidationError

if TYPE_CHECKING:
    from .person import Customer


class DiscountPolicy(ABC):
    """Chiến lược tính số tiền được giảm cho một đơn hàng."""

    @property
    @abstractmethod
    def code(self) -> str:
        """Mã định danh chính sách."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Mô tả hiển thị cho người dùng."""

    @abstractmethod
    def calculate(self, subtotal: float, customer: "Customer | None", quantity: int) -> float:
        """Trả về số tiền được giảm (VND)."""

    def __str__(self) -> str:
        return self.description


class NoDiscount(DiscountPolicy):
    """Không giảm giá."""

    CODE = "NONE"

    @property
    def code(self) -> str:
        return self.CODE

    @property
    def description(self) -> str:
        return "Không áp dụng giảm giá"

    def calculate(self, subtotal: float, customer: "Customer | None", quantity: int) -> float:
        return 0.0


class VIPDiscount(DiscountPolicy):
    """Chiết khấu theo tỷ lệ của hạng VIP mà khách đang có."""

    CODE = "VIP_TIER"

    @property
    def code(self) -> str:
        return self.CODE

    @property
    def description(self) -> str:
        return "Chiết khấu theo hạng VIP (5% – 20%)"

    def calculate(self, subtotal: float, customer: "Customer | None", quantity: int) -> float:
        if customer is None:
            return 0.0
        return float(round(subtotal * customer.discount_rate))


class ConditionalPercentDiscount(DiscountPolicy):
    """Giảm một tỷ lệ cố định khi đơn hàng thỏa điều kiện – lớp con chỉ định nghĩa điều kiện."""

    def __init__(self, rate: float) -> None:
        if not 0 < rate < 1:
            raise ValidationError("Tỷ lệ giảm phải nằm trong khoảng (0, 1)")
        self._rate = rate

    @property
    def rate(self) -> float:
        return self._rate

    @abstractmethod
    def is_eligible(self, subtotal: float, customer: "Customer | None", quantity: int) -> bool:
        """Đơn hàng có đủ điều kiện hưởng giảm giá hay không."""

    def calculate(self, subtotal: float, customer: "Customer | None", quantity: int) -> float:
        if not self.is_eligible(subtotal, customer, quantity):
            return 0.0
        return float(round(subtotal * self._rate))


class SeasonalPromotion(ConditionalPercentDiscount):
    """Khuyến mãi mùa: giảm % cho đơn đạt giá trị tối thiểu."""

    CODE = "SEASONAL_12"

    def __init__(self, min_subtotal: float = 250_000, rate: float = 0.12) -> None:
        super().__init__(rate)
        self._min_subtotal = min_subtotal

    @property
    def code(self) -> str:
        return self.CODE

    @property
    def description(self) -> str:
        return f"Mùa đọc sách: -{self._rate:.0%} cho đơn từ {self._min_subtotal:,.0f}đ".replace(",", ".")

    def is_eligible(self, subtotal: float, customer: "Customer | None", quantity: int) -> bool:
        return subtotal >= self._min_subtotal


class BulkOrderDiscount(ConditionalPercentDiscount):
    """Mua nhiều: giảm % khi tổng số lượng đạt mức tối thiểu."""

    CODE = "BULK_15"

    def __init__(self, min_quantity: int = 4, rate: float = 0.15) -> None:
        super().__init__(rate)
        self._min_quantity = min_quantity

    @property
    def code(self) -> str:
        return self.CODE

    @property
    def description(self) -> str:
        return f"Mua nhiều: -{self._rate:.0%} khi mua từ {self._min_quantity} cuốn"

    def is_eligible(self, subtotal: float, customer: "Customer | None", quantity: int) -> bool:
        return quantity >= self._min_quantity


class DiscountRegistry:
    """Danh mục các chính sách giảm giá đang áp dụng."""

    def __init__(self, policies: Iterable[DiscountPolicy] = ()) -> None:
        self._policies: dict[str, DiscountPolicy] = {}
        for policy in policies:
            self.register(policy)

    @classmethod
    def default(cls) -> "DiscountRegistry":
        return cls([NoDiscount(), VIPDiscount(), SeasonalPromotion(), BulkOrderDiscount()])

    def register(self, policy: DiscountPolicy) -> None:
        self._policies[policy.code] = policy

    def get(self, code: str) -> DiscountPolicy:
        try:
            return self._policies[code]
        except KeyError:
            raise ValidationError(f"Mã giảm giá không tồn tại: '{code}'") from None

    def all(self) -> list[DiscountPolicy]:
        return list(self._policies.values())

    def best_for(self, subtotal: float, customer: "Customer | None", quantity: int) -> DiscountPolicy:
        """Chọn chính sách có lợi nhất cho khách (đa hình: mỗi chính sách tự tính số tiền giảm).

        Các chính sách không cộng dồn; khi bằng nhau thì ưu tiên chính sách đăng ký trước.
        """
        if not self._policies:
            raise ValidationError("Chưa cấu hình chính sách giảm giá nào")
        return max(self._policies.values(), key=lambda policy: policy.calculate(subtotal, customer, quantity))
