"""Observer Pattern cho vòng đời đơn hàng.

``OrderService`` không cần biết ai quan tâm tới việc đơn được xác nhận / hủy; nó chỉ
thông báo cho các listener đã đăng ký:

- ``InventoryService``   – hủy đơn thì hoàn sách về kho
- ``CustomerService``    – xác nhận đơn thì cộng chi tiêu & điểm tích lũy
- ``MembershipService``  – xác nhận đơn hội viên thì kích hoạt / gia hạn gói
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Order


class OrderListener(ABC):
    """Giao diện cho các lớp muốn phản ứng khi trạng thái đơn hàng thay đổi."""

    @abstractmethod
    def order_completed(self, order: "Order") -> None:
        """Gọi sau khi đơn được xác nhận hoàn tất."""

    @abstractmethod
    def order_cancelled(self, order: "Order") -> None:
        """Gọi sau khi đơn bị hủy."""
