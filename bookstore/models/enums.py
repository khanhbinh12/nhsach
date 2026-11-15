"""Các kiểu liệt kê (Enum) dùng trong hệ thống."""

from __future__ import annotations

from enum import Enum


class ProductFormat(str, Enum):
    PHYSICAL = "PHYSICAL"
    EBOOK = "EBOOK"
    MEMBERSHIP = "MEMBERSHIP"

    @property
    def label(self) -> str:
        return {"PHYSICAL": "Sách giấy", "EBOOK": "E-Book", "MEMBERSHIP": "Gói hội viên"}[self.value]


class VIPTier(str, Enum):
    STANDARD = "STANDARD"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"

    @property
    def rank(self) -> int:
        """Thứ bậc của hạng, dùng để so sánh hạng cao/thấp."""
        return list(VIPTier).index(self)

    @property
    def label(self) -> str:
        return {
            "STANDARD": "Thường",
            "BRONZE": "Đồng",
            "SILVER": "Bạc",
            "GOLD": "Vàng",
            "PLATINUM": "Bạch kim",
        }[self.value]


class OrderType(str, Enum):
    ONLINE = "ONLINE"
    MEMBERSHIP = "MEMBERSHIP"

    @property
    def label(self) -> str:
        return {"ONLINE": "Mua sách", "MEMBERSHIP": "Hội viên E-Book"}[self.value]

    @property
    def charges_shipping(self) -> bool:
        """Chỉ đơn sách giấy mới tính phí vận chuyển."""
        return self is OrderType.ONLINE


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SHIPPING = "SHIPPING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @property
    def label(self) -> str:
        return {"PENDING": "Chờ xử lý", "SHIPPING": "Đang giao", "COMPLETED": "Hoàn tất",
                "CANCELLED": "Đã hủy"}[self.value]


class OrderAction(str, Enum):
    """Các thao tác quản trị viên có thể thực hiện trên một đơn hàng."""

    SHIP = "ship"
    COMPLETE = "complete"
    CANCEL = "cancel"

    @property
    def label(self) -> str:
        return {"ship": "Giao hàng", "complete": "Hoàn tất", "cancel": "Hủy đơn"}[self.value]
