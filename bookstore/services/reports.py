"""Dịch vụ báo cáo – chỉ đọc dữ liệu. Doanh thu chỉ tính đơn đã hoàn tất."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..models import Order, OrderStatus, OrderType, ProductFormat
from .ads import AdService
from .customers import CustomerService
from .inventory import InventoryService
from .membership import MembershipService
from .orders import OrderService


@dataclass(frozen=True)
class DashboardSummary:
    book_revenue: float
    membership_revenue: float
    ad_revenue: float
    completed_orders: int
    pending_orders: int
    shipping_orders: int
    product_count: int
    physical_stock: int
    customer_count: int
    active_members: int
    low_stock_count: int
    ad_views: int

    @property
    def total_revenue(self) -> float:
        return self.book_revenue + self.membership_revenue + self.ad_revenue

    @property
    def side_income(self) -> float:
        """Thu nhập phụ: hội viên E-Book + quảng cáo."""
        return self.membership_revenue + self.ad_revenue


@dataclass(frozen=True)
class TopSeller:
    product_id: str
    title: str
    format: ProductFormat
    quantity: int
    revenue: float


class ReportService:
    def __init__(
        self,
        inventory: InventoryService,
        customers: CustomerService,
        orders: OrderService,
        membership: MembershipService,
        ads: AdService,
    ) -> None:
        self._inventory = inventory
        self._customers = customers
        self._orders = orders
        self._membership = membership
        self._ads = ads

    def _completed(self) -> list[Order]:
        return [o for o in self._orders.stored() if o.status is OrderStatus.COMPLETED]  # báo cáo không cần sắp xếp

    def summary(self) -> DashboardSummary:
        completed = self._completed()
        membership = sum(o.final_total for o in completed if o.order_type is OrderType.MEMBERSHIP)
        books = sum(o.final_total for o in completed if o.order_type is OrderType.ONLINE)
        return DashboardSummary(
            book_revenue=books,
            membership_revenue=membership,
            ad_revenue=self._ads.estimated_revenue(),
            completed_orders=len(completed),
            pending_orders=self._orders.count(OrderStatus.PENDING),
            shipping_orders=self._orders.count(OrderStatus.SHIPPING),
            product_count=len(self._inventory),
            physical_stock=self._inventory.total_physical_stock(),
            customer_count=len(self._customers),
            active_members=len(self._membership.active_members()),
            low_stock_count=len(self._inventory.low_stock()),
            ad_views=self._ads.ledger.total_views,
        )

    def top_sellers(self, limit: int = 5) -> list[TopSeller]:
        totals: dict[str, list] = {}
        for order in self._completed():
            for line in order.lines:
                if line.format is ProductFormat.MEMBERSHIP:
                    continue
                entry = totals.setdefault(line.product_id, [line.title, line.format, 0, 0.0])
                entry[2] += line.quantity
                entry[3] += line.subtotal
        sellers = [TopSeller(pid, *values) for pid, values in totals.items()]
        return sorted(sellers, key=lambda s: (s.quantity, s.revenue), reverse=True)[:limit]

    def revenue_by_category(self) -> list[tuple[str, float]]:
        """Doanh số theo thể loại (giá niêm yết, trước giảm giá) của các đơn đã hoàn tất."""
        totals: dict[str, float] = {}
        for order in self._completed():
            for line in order.lines:
                totals[line.category] = totals.get(line.category, 0.0) + line.subtotal
        return sorted(totals.items(), key=lambda item: item[1], reverse=True)

    def ad_views_recent(self, today: date, days: int = 7) -> list[tuple[date, int]]:
        return self._ads.ledger.recent(today, days)
