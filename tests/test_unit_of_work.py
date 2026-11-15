"""Kiểm thử Unit of Work: chỉ ghi đối tượng thay đổi, nhưng KHÔNG được bỏ sót thay đổi nào.

Rủi ro lớn nhất của Unit of Work: một thao tác sửa dữ liệu mà không bị đánh dấu "đã thay đổi"
→ mất dữ liệu khi khởi động lại. Bài test ``test_every_command_survives_restart`` chạy mọi loại
lệnh ghi, sau MỖI lệnh đọc lại từ file SQLite và so với dữ liệu trong bộ nhớ.
"""

import tempfile
import unittest
from pathlib import Path

from bookstore.models import Cart, PhysicalBook
from bookstore.services import Bookstore
from bookstore.storage import SqliteStorage

from .helpers import FakeClock

COD = "Thanh toán khi nhận hàng (COD)"


class TrackableTest(unittest.TestCase):
    def test_new_object_is_dirty_and_setter_marks_dirty(self):
        book = PhysicalBook(title="A", author="B", price=1000, stock=5)
        self.assertTrue(book.is_dirty)
        book.mark_clean()
        self.assertFalse(book.is_dirty)
        _ = book.title, book.stock_label(), book.to_dict()  # chỉ đọc → vẫn sạch
        self.assertFalse(book.is_dirty)
        book.take_from_stock(1)
        self.assertTrue(book.is_dirty)

    def test_customer_dirty_when_membership_changes(self):
        store = Bookstore(_memory())
        customer = store.customers.get("KH-REG04")
        customer.mark_clean()
        customer.membership.renew(days=30, fee=0, payment_ref="X")
        self.assertTrue(customer.is_dirty)


def _memory():
    from bookstore.storage import InMemoryStorage

    return InMemoryStorage()


class SqliteUnitOfWorkTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "bookstore.db"
        self.clock = FakeClock()
        self.storage = SqliteStorage(self.path)
        self.store = Bookstore(self.storage, clock=self.clock)

    def assert_persisted(self, label):
        reloaded = Bookstore(SqliteStorage(self.path), clock=self.clock)
        self.assertEqual(reloaded.to_dict(), self.store.to_dict(), f"Mất dữ liệu sau lệnh: {label}")

    def test_only_changed_objects_are_serialized(self):
        self.store.restock("BK-OOP-01", 2)
        self.assertEqual(self.storage.last_changes, {"inserted": 0, "updated": 1, "deleted": 0})
        self.assertEqual(self.store._unit_of_work.collect().dirty_count, 0)  # đã ghi xong thì sạch

    def test_every_command_survives_restart(self):
        store = self.store
        account = store.register_customer(name="Khách Mới", phone="0977000111", email="moi@example.com",
                                           password="matkhau1")
        customer = store.accounts.customer_of(account)
        self.assert_persisted("đăng ký")

        store.change_password(account.id, "matkhau1", "matkhau2")
        self.assert_persisted("đổi mật khẩu")

        cart = Cart()
        cart.add(store.inventory.get("BK-OOP-01"), 2)
        order = store.place_order(cart, customer=customer, payment_method=COD, shipping_address="1 Lê Lợi",
                                  voucher_code="GIAM30K")
        self.assert_persisted("đặt hàng có mã giảm giá (trừ kho + trừ lượt mã)")

        store.ship_order(order.id)
        self.assert_persisted("giao hàng")
        store.complete_order(order.id)
        self.assert_persisted("hoàn tất (cộng điểm khách)")

        cart = Cart()
        cart.add(store.inventory.get("BK-LIT-02"), 1)
        cancelled = store.place_order(cart, customer=customer, payment_method=COD, shipping_address="1 Lê Lợi")
        store.cancel_own_order(customer, cancelled.id)
        self.assert_persisted("khách tự hủy (hoàn kho)")

        membership = store.request_membership(customer)
        self.assert_persisted("yêu cầu hội viên")
        store.complete_order(membership.id)
        self.assert_persisted("kích hoạt hội viên (đối tượng con thay đổi)")
        store.revoke_membership(customer.id)
        self.assert_persisted("thu hồi hội viên")
        store.grant_membership(customer.id)
        self.assert_persisted("tặng hội viên")

        store.promote_to_vip(customer.id, "GOLD")
        self.assert_persisted("nâng VIP (thay đối tượng)")

        product = store.create_product({"format": "EBOOK", "title": "Sách mới", "author": "Tác giả"})
        self.assert_persisted("thêm sách")
        store.update_product(product.id, {"title": "Sách mới (sửa)", "drive_link": "https://drive.google.com/x"})
        self.assert_persisted("sửa sách")
        store.restock("BK-LIT-04", 7)
        self.assert_persisted("nhập kho")
        store.delete_product("BK-SCI-05")
        self.assert_persisted("xóa sách")

        store.create_voucher({"kind": "PERCENT", "code": "MOI10", "value": 10})
        store.set_voucher_active("MOI10", False)
        self.assert_persisted("tạo & tắt mã")
        store.delete_voucher("MOI10")
        self.assert_persisted("xóa mã")

        store.update_vault({"membership_fee": 120000})
        store.update_ad_settings({"duration_seconds": 20})
        self.assert_persisted("cấu hình")

        session = store.start_ad("viewer")
        self.clock.advance(seconds=30)
        store.complete_ad(session.token, "viewer")
        self.assert_persisted("xem quảng cáo")

        store.reset_sample_data()
        self.assert_persisted("đặt lại dữ liệu mẫu")


if __name__ == "__main__":
    unittest.main()
