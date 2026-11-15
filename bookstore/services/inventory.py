"""Dịch vụ quản lý kho sách."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, cast

from ..exceptions import NotFoundError, ValidationError
from ..models import DEFAULT_IDS, EBook, IdGenerator, Order, Product, ProductFactory, ProductFormat
from ..models.validators import optional_text
from .events import OrderListener


class InventoryService(OrderListener):
    """Quản lý danh mục sản phẩm; lắng nghe sự kiện hủy đơn để hoàn kho."""

    LOW_STOCK_THRESHOLD = 5

    def __init__(self, products: Iterable[Product] = (), ids: IdGenerator = DEFAULT_IDS) -> None:
        self._ids = ids
        self._products: dict[str, Product] = {}
        for product in products:
            self.add(product)

    # -------------------------------------------------------------- truy vấn
    def find(self, product_id: str | None) -> Product | None:
        return self._products.get(product_id or "")

    def get(self, product_id: str) -> Product:
        product = self.find(product_id)
        if product is None:
            raise NotFoundError(f"Không tìm thấy sách có mã '{product_id}'")
        return product

    def all(self) -> list[Product]:
        return list(self._products.values())

    def by_format(self, fmt: ProductFormat) -> list[Product]:
        return [p for p in self._products.values() if p.format is fmt]

    def ebooks(self) -> list[EBook]:
        return cast("list[EBook]", self.by_format(ProductFormat.EBOOK))

    def search(self, keyword: str = "", fmt: ProductFormat | None = None, category: str | None = None) -> list[Product]:
        key = keyword.strip().lower()
        results = []
        for product in self._products.values():
            if key and key not in f"{product.id} {product.title} {product.byline()}".lower():
                continue
            if fmt is not None and product.format is not fmt:
                continue
            if category and product.category != category:
                continue
            results.append(product)
        return results

    def catalog(self, keyword: str = "", category: str | None = None) -> list[Product]:
        """Sản phẩm bán lẻ trên web (đa hình qua ``purchasable``)."""
        return [p for p in self.search(keyword, category=category) if p.purchasable]

    def low_stock(self, threshold: int | None = None) -> list[Product]:
        limit = self.LOW_STOCK_THRESHOLD if threshold is None else threshold
        return [p for p in self._products.values() if p.is_low_stock(limit)]

    def categories(self, products: Iterable[Product] | None = None) -> list[str]:
        source = self._products.values() if products is None else products
        return sorted({p.category for p in source})

    def total_physical_stock(self) -> int:
        return sum(p.stock for p in self._products.values() if p.tracks_stock)

    def __len__(self) -> int:
        return len(self._products)

    # ------------------------------------------------------------- thay đổi
    def add(self, product: Product) -> Product:
        if product.id in self._products:
            raise ValidationError(f"Mã sách '{product.id}' đã tồn tại")
        self._products[product.id] = product
        return product

    def create(self, data: Mapping[str, Any]) -> Product:
        if not optional_text(data.get("id")):
            # Admin không nhập mã: sinh mã chưa dùng theo tiền tố của đúng loại sách (BK-...).
            prefix = ProductFactory.class_for(data).ID_PREFIX
            data = {**data, "id": self._ids.new_id(prefix, self._products.__contains__)}
        return self.add(ProductFactory.create(data))

    def update(self, product_id: str, changes: Mapping[str, Any]) -> Product:
        product = self.get(product_id)
        # Kiểm tra trước trên một bản sao: nếu dữ liệu sai thì đối tượng gốc không bị sửa dở dang.
        ProductFactory.create({**product.to_dict(), **changes, "id": product.id, "format": product.format.value})
        product.apply_changes(changes)
        return product

    def remove(self, product_id: str) -> Product:
        product = self.get(product_id)
        del self._products[product_id]
        return product

    def restock(self, product_id: str, quantity: int | str) -> Product:
        product = self.get(product_id)
        product.restock(quantity)  # đa hình: sản phẩm số sẽ báo UnsupportedOperationError
        return product

    # ------------------------------------------------------- OrderListener
    def order_completed(self, order: Order) -> None:
        """Hàng đã được trừ kho lúc đặt đơn nên không cần làm gì thêm."""

    def order_cancelled(self, order: Order) -> None:
        for line in order.lines:
            product = self.find(line.product_id)
            if product is not None:
                product.return_to_stock(line.quantity)  # đa hình: sách số không làm gì
