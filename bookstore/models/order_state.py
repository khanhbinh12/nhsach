"""State Pattern cho vòng đời đơn hàng.

    Đơn sách:      PENDING ──ship()──▶ SHIPPING ──complete()──▶ COMPLETED
                      │                    │
                      └──cancel()──▶ CANCELLED ◀──cancel()──┘   (giao thất bại)

    Đơn hội viên:  PENDING ──complete()──▶ COMPLETED   (không cần giao hàng)

Mỗi trạng thái là một lớp; nó tự quyết định thao tác nào hợp lệ và trạng thái kế tiếp là gì,
nên ``Order`` không cần chuỗi if/elif theo trạng thái. Thêm trạng thái mới chỉ cần thêm một lớp.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from ..exceptions import ValidationError
from .enums import OrderAction, OrderStatus

if TYPE_CHECKING:
    from .order import Order


class OrderState(ABC):
    """Trạng thái gốc: mặc định mọi thao tác đều không hợp lệ – lớp con mở các thao tác được phép."""

    STATUS: ClassVar[OrderStatus]
    _registry: ClassVar[dict[OrderStatus, type["OrderState"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        OrderState._registry[cls.STATUS] = cls

    @staticmethod
    def for_status(status: OrderStatus) -> "OrderState":
        return OrderState._registry[OrderStatus(status)]()

    @property
    def status(self) -> OrderStatus:
        return self.STATUS

    @abstractmethod
    def hint(self, order: "Order") -> str:
        """Giải thích trạng thái cho khách hàng."""

    @property
    def customer_can_cancel(self) -> bool:
        """Khách có được tự hủy đơn ở trạng thái này không."""
        return False

    def actions(self, order: "Order") -> tuple[OrderAction, ...]:
        """Các thao tác quản trị hợp lệ – giao diện dựa vào đây để hiện nút."""
        return ()

    def ship(self, order: "Order") -> "OrderState":
        raise self._invalid(order, "giao")

    def complete(self, order: "Order") -> "OrderState":
        raise self._invalid(order, "hoàn tất")

    def cancel(self, order: "Order") -> "OrderState":
        raise self._invalid(order, "hủy")

    def _invalid(self, order: "Order", action: str) -> ValidationError:
        return ValidationError(f"Không thể {action} đơn {order.id} vì đơn đang ở trạng thái '{self.STATUS.label}'")


class PendingState(OrderState):
    """Chờ xử lý: đơn sách thì đem đi giao, đơn hội viên thì xác nhận thẳng."""

    STATUS = OrderStatus.PENDING

    def hint(self, order: "Order") -> str:
        if order.order_type.charges_shipping:
            return "Nhà sách đang chuẩn bị hàng. Bạn vẫn có thể tự hủy đơn trước khi đơn được giao."
        return "Nhà sách đang kiểm tra giao dịch chuyển khoản; gói sẽ được kích hoạt ngay khi xác nhận."

    @property
    def customer_can_cancel(self) -> bool:
        return True

    def actions(self, order: "Order") -> tuple[OrderAction, ...]:
        first = OrderAction.SHIP if order.order_type.charges_shipping else OrderAction.COMPLETE
        return first, OrderAction.CANCEL

    def ship(self, order: "Order") -> OrderState:
        if not order.order_type.charges_shipping:
            raise ValidationError(f"Đơn {order.id} là đơn hội viên, không cần giao hàng")
        return ShippingState()

    def complete(self, order: "Order") -> OrderState:
        if order.order_type.charges_shipping:
            raise ValidationError(f"Đơn {order.id} phải được giao trước khi hoàn tất")
        return CompletedState()

    def cancel(self, order: "Order") -> OrderState:
        return CancelledState()


class ShippingState(OrderState):
    """Đang giao: giao thành công thì hoàn tất, giao thất bại thì hủy (hoàn kho)."""

    STATUS = OrderStatus.SHIPPING

    def hint(self, order: "Order") -> str:
        return "Đơn đang được giao tới bạn. Cần hỗ trợ vui lòng liên hệ nhà sách."

    def actions(self, order: "Order") -> tuple[OrderAction, ...]:
        return OrderAction.COMPLETE, OrderAction.CANCEL

    def complete(self, order: "Order") -> OrderState:
        return CompletedState()

    def cancel(self, order: "Order") -> OrderState:
        return CancelledState()


class CompletedState(OrderState):
    """Hoàn tất: trạng thái cuối, không thao tác nào được phép."""

    STATUS = OrderStatus.COMPLETED

    def hint(self, order: "Order") -> str:
        if order.order_type.charges_shipping:
            return "Đơn đã giao thành công. Cảm ơn bạn đã ủng hộ nhà sách!"
        return "Gói hội viên đã được kích hoạt – vào Kho E-Book để xem link Drive."


class CancelledState(OrderState):
    """Đã hủy: trạng thái cuối, không thao tác nào được phép."""

    STATUS = OrderStatus.CANCELLED

    def hint(self, order: "Order") -> str:
        return "Đơn đã bị hủy."
