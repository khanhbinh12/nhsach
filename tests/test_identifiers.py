"""Kiểm thử sinh mã không trùng (lỗi được phát hiện khi đo hiệu năng với ~2.000 sách)."""

import unittest

from bookstore.exceptions import BookstoreError
from bookstore.models import Cart, IdGenerator
from bookstore.services import Bookstore, CustomerService, InventoryService
from bookstore.storage import InMemoryStorage


class ScriptedRandom:
    """Nguồn "ngẫu nhiên" trả về lần lượt các giá trị cho trước – để cố tình tạo trùng mã."""

    def __init__(self, *values: str) -> None:
        self._values = list(values)

    def __call__(self, length: int) -> str:
        return self._values.pop(0)


class IdGeneratorTest(unittest.TestCase):
    def test_retries_until_unused(self):
        generator = IdGenerator(random_part=ScriptedRandom("AAAA", "AAAA", "BBBB"))
        taken = {"BK-AAAA"}
        self.assertEqual(generator.new_id("BK", taken.__contains__), "BK-BBBB")

    def test_gives_up_with_clear_error(self):
        generator = IdGenerator(random_part=lambda length: "AAAA")
        with self.assertRaises(BookstoreError):
            generator.new_id("BK", lambda candidate: True)

    def test_default_format(self):
        new_id = IdGenerator().new_id("KH")
        self.assertRegex(new_id, r"^KH-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{8}$")


class ServiceUniqueIdTest(unittest.TestCase):
    """Dịch vụ phải tự né mã đã tồn tại thay vì báo lỗi "đã tồn tại" cho người dùng."""

    BOOK = {"format": "PHYSICAL", "title": "Sách", "author": "Tác giả", "price": 100000, "stock": 1}

    def test_inventory_skips_existing_product_id(self):
        inventory = InventoryService(ids=IdGenerator(random_part=ScriptedRandom("TRUNG", "TRUNG", "MOI")))
        first = inventory.create(self.BOOK)
        second = inventory.create(self.BOOK)  # lần sinh đầu trùng "BK-TRUNG" → phải tự sinh lại
        self.assertEqual(first.id, "BK-TRUNG")
        self.assertEqual(second.id, "BK-MOI")

    def test_customer_service_skips_existing_id(self):
        customers = CustomerService(ids=IdGenerator(random_part=ScriptedRandom("TRUNG", "TRUNG", "MOI")))
        customers.register(name="A", phone="0911000001")
        self.assertEqual(customers.register(name="B", phone="0911000002").id, "KH-MOI")

    def test_order_ids_unique_and_dated(self):
        store = Bookstore(InMemoryStorage())
        customer = store.customers.get("KH-REG03")
        book = store.inventory.get("BK-LIT-02")
        ids = set()
        for _ in range(30):
            cart = Cart()
            cart.add(book, 1)
            order = store.place_order(cart, customer=customer, payment_method="Thanh toán khi nhận hàng (COD)",
                                      shipping_address="1 Lê Lợi")
            ids.add(order.id)
            self.assertTrue(order.id.startswith(f"HD-{order.created_at:%y%m%d}-"))
        self.assertEqual(len(ids), 30)

    def test_many_products_without_ids(self):
        """Tái hiện đúng tình huống lỗi: thêm hàng nghìn sách không nhập mã."""
        inventory = InventoryService()
        for i in range(3000):
            inventory.create({**self.BOOK, "title": f"Sách {i}"})
        self.assertEqual(len(inventory), 3000)


if __name__ == "__main__":
    unittest.main()
