"""Giỏ hàng lưu trong session của trình duyệt (Adapter giữa session Flask và lớp ``Cart``)."""

from __future__ import annotations

from flask import session

from ..exceptions import BookstoreError
from ..models import Cart, Product
from ..services import InventoryService


class SessionCart:
    """Session chỉ lưu {mã sách: số lượng}; mỗi request dựng lại đối tượng ``Cart`` từ kho hiện tại."""

    KEY = "cart"

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory

    def _raw(self) -> dict[str, int]:
        raw = session.get(self.KEY) or {}
        return {str(k): int(v) for k, v in raw.items() if str(v).isdigit()}

    def build(self) -> Cart:
        """Bỏ qua sách đã bị xóa / hết hàng để giỏ luôn hợp lệ."""
        cart = Cart()
        for product_id, quantity in self._raw().items():
            product = self._inventory.find(product_id)
            if product is None:
                continue
            try:
                cart.add(product, quantity)
            except BookstoreError:
                continue
        self._save(cart)
        return cart

    def add(self, product: Product, quantity: int | str = 1) -> None:
        cart = self.build()
        cart.add(product, quantity)
        self._save(cart)

    def update(self, product_id: str, quantity: int) -> None:
        cart = self.build()
        cart.set_quantity(product_id, quantity)
        self._save(cart)

    def remove(self, product_id: str) -> None:
        cart = self.build()
        cart.remove(product_id)
        self._save(cart)

    def clear(self) -> None:
        session.pop(self.KEY, None)

    def count(self) -> int:
        return sum(self._raw().values())

    def _save(self, cart: Cart) -> None:
        new_value = {product.id: quantity for product, quantity in cart.items()}
        if session.get(self.KEY) != new_value:
            session[self.KEY] = new_value
