"""Kiểm thử tầng dịch vụ (Facade Bookstore) và lưu trữ."""

import json
import tempfile
import unittest
from pathlib import Path

from bookstore.exceptions import (
    AccessDeniedError,
    AuthenticationError,
    BookstoreError,
    DataCorruptedError,
    OutOfStockError,
    ValidationError,
)
from bookstore.models import Cart, OrderStatus, OrderType
from bookstore.services import Bookstore, CoverImageStore
from bookstore.storage import InMemoryStorage, JsonFileStorage, SqliteStorage

from .helpers import FakeClock, make_image

COD = "Thanh toán khi nhận hàng (COD)"


class BookstoreTestCase(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.storage = InMemoryStorage()
        self.store = Bookstore(self.storage, clock=self.clock)

    def reload(self):
        return Bookstore(self.storage, clock=self.clock)

    def new_customer(self, phone="0977000111", email="moi@example.com"):
        account = self.store.register_customer(name="Khách Mới", phone=phone, email=email, password="matkhau1")
        return self.store.accounts.customer_of(account)

    def deliver(self, order):
        """Đơn sách phải giao rồi mới hoàn tất (State Pattern)."""
        self.store.ship_order(order.id)
        return self.store.complete_order(order.id)

    def order(self, customer, items, **kwargs):
        cart = Cart()
        for product_id, quantity in items:
            cart.add(self.store.inventory.get(product_id), quantity)
        return self.store.place_order(cart, customer=customer, payment_method=COD,
                                      shipping_address=kwargs.get("address", "1 Lê Lợi"),
                                      voucher_code=kwargs.get("voucher", ""))


class DataTest(BookstoreTestCase):
    def test_sample_data_survives_reload(self):
        reloaded = self.reload()
        self.assertEqual(reloaded.to_dict(), self.store.to_dict())
        self.assertEqual(len(reloaded.customers), 4)

    def test_ebooks_are_not_in_shop_catalog(self):
        catalog = self.store.inventory.catalog()
        self.assertTrue(catalog)
        self.assertTrue(all(p.purchasable for p in catalog))
        self.assertTrue(self.store.inventory.ebooks())


class AccountTest(BookstoreTestCase):
    def test_register_and_login_by_email_or_phone(self):
        self.new_customer()
        self.assertEqual(self.store.authenticate("moi@example.com", "matkhau1").login, "moi@example.com")
        self.assertEqual(self.store.authenticate("0977000111", "matkhau1").login, "moi@example.com")
        with self.assertRaises(AuthenticationError):
            self.store.authenticate("moi@example.com", "sai-mat-khau")

    def test_duplicate_phone_or_email_is_rejected_without_side_effects(self):
        customers_before = len(self.store.customers)
        with self.assertRaises(ValidationError):
            self.store.register_customer(name="Trùng", phone="0912345678", email="khac@example.com", password="123456")
        with self.assertRaises(ValidationError):
            self.store.register_customer(name="Trùng", phone="0999888777", email="nam.nt@example.com", password="123456")
        self.assertEqual(len(self.store.customers), customers_before)


class OrderFlowTest(BookstoreTestCase):
    def test_new_order_is_pending_and_reserves_stock(self):
        customer = self.new_customer()
        book = self.store.inventory.get("BK-LIT-02")
        before = book.stock
        order = self.order(customer, [("BK-LIT-02", 2)])
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(book.stock, before - 2)
        self.assertEqual(customer.total_spent, 0)  # chưa xác nhận thì chưa tính chi tiêu

    def test_complete_records_purchase_via_observer(self):
        customer = self.new_customer()
        order = self.order(customer, [("BK-OOP-01", 1)])
        self.deliver(order)
        self.assertEqual(customer.total_spent, order.final_total)
        self.assertGreater(customer.loyalty_points, 0)

    def test_cancel_returns_stock_via_observer(self):
        customer = self.new_customer()
        book = self.store.inventory.get("BK-LIT-02")
        before = book.stock
        order = self.order(customer, [("BK-LIT-02", 3)])
        self.store.cancel_order(order.id)
        self.assertEqual(book.stock, before)
        with self.assertRaises(ValidationError):
            self.store.complete_order(order.id)

    def test_customer_cannot_cancel_someone_elses_order(self):
        owner = self.new_customer()
        other = self.new_customer(phone="0977000222", email="khac@example.com")
        order = self.order(owner, [("BK-OOP-01", 1)])
        with self.assertRaises(BookstoreError):
            self.store.cancel_own_order(other, order.id)

    def test_place_order_is_all_or_nothing(self):
        customer = self.new_customer()
        plenty = self.store.inventory.get("BK-LIT-02")
        scarce = self.store.inventory.get("BK-LIT-04")
        cart = Cart()
        cart.add(plenty, 1)
        cart.add(scarce, 1)
        scarce.stock = 0  # hết hàng sau khi đã cho vào giỏ
        stock_before, orders_before = plenty.stock, len(self.store.orders)
        with self.assertRaises(OutOfStockError):
            self.store.place_order(cart, customer=customer, payment_method=COD, shipping_address="1 Lê Lợi")
        self.assertEqual(plenty.stock, stock_before)
        self.assertEqual(len(self.store.orders), orders_before)

    def test_orders_keep_original_prices(self):
        customer = self.new_customer()
        order = self.order(customer, [("BK-OOP-01", 1)])
        total = order.final_total
        self.store.update_product("BK-OOP-01", {"price": 999_000})
        self.assertEqual(self.reload().orders.get(order.id).final_total, total)

    def test_best_discount_applied_automatically(self):
        customer = self.new_customer()
        order = self.order(customer, [("BK-LIT-02", 4)])  # 480.000đ, 4 cuốn → giảm 15% tốt hơn 12%
        self.assertEqual(order.discount_code, "BULK_15")
        self.assertEqual(order.discount_amount, 72_000)

    def test_revenue_counts_only_completed_orders(self):
        before = self.store.reports.summary().book_revenue
        customer = self.new_customer()
        order = self.order(customer, [("BK-OOP-01", 1)])
        self.assertEqual(self.store.reports.summary().book_revenue, before)
        self.deliver(order)
        self.assertEqual(self.store.reports.summary().book_revenue, before + order.final_total)

    def test_invalid_update_leaves_product_untouched(self):
        book = self.store.inventory.get("BK-OOP-01")
        before = book.to_dict()
        with self.assertRaises(ValidationError):
            self.store.update_product(book.id, {"title": "Tên mới", "price": "abc"})
        self.assertEqual(book.to_dict(), before)


class OrderStateFlowTest(BookstoreTestCase):
    def test_cancel_while_shipping_returns_stock(self):
        customer = self.new_customer()
        book = self.store.inventory.get("BK-LIT-02")
        before = book.stock
        order = self.order(customer, [("BK-LIT-02", 2)])
        self.store.ship_order(order.id)
        self.store.cancel_order(order.id)  # giao thất bại
        self.assertEqual(book.stock, before)

    def test_customer_cannot_cancel_after_shipping(self):
        customer = self.new_customer()
        order = self.order(customer, [("BK-OOP-01", 1)])
        self.store.ship_order(order.id)
        with self.assertRaises(BookstoreError):
            self.store.cancel_own_order(customer, order.id)

    def test_book_order_cannot_skip_shipping(self):
        order = self.order(self.new_customer(), [("BK-OOP-01", 1)])
        with self.assertRaises(ValidationError):
            self.store.complete_order(order.id)


class VoucherFlowTest(BookstoreTestCase):
    def test_voucher_applied_and_counted(self):
        voucher = self.store.vouchers.get("GIAM30K")
        order = self.order(self.new_customer(), [("BK-OOP-01", 1)], voucher="giam30k")  # 185.000đ
        self.assertEqual(order.discount_code, "GIAM30K")
        self.assertEqual(order.discount_amount, 30_000)
        self.assertEqual(voucher.used_count, 1)

    def test_cancel_releases_voucher_use(self):
        voucher = self.store.vouchers.get("GIAM30K")
        order = self.order(self.new_customer(), [("BK-OOP-01", 1)], voucher="GIAM30K")
        self.store.cancel_order(order.id)
        self.assertEqual(voucher.used_count, 0)

    def test_better_automatic_discount_wins_and_voucher_not_consumed(self):
        voucher = self.store.vouchers.get("GIAM30K")
        order = self.order(self.new_customer(), [("BK-LIT-02", 4)], voucher="GIAM30K")  # -15% = 72.000đ
        self.assertEqual(order.discount_code, "BULK_15")
        self.assertEqual(voucher.used_count, 0)

    def test_invalid_voucher_blocks_order_without_side_effects(self):
        book = self.store.inventory.get("BK-OOP-01")
        before = book.stock
        with self.assertRaises(ValidationError):
            self.order(self.new_customer(), [("BK-OOP-01", 1)], voucher="KHONGCO")
        with self.assertRaisesRegex(ValidationError, "200.000"):
            self.order(self.new_customer(phone="0977000999", email="b@example.com"), [("BK-OOP-01", 1)],
                       voucher="TRITRI10")
        self.assertEqual(book.stock, before)

    def test_expired_voucher(self):
        self.store.create_voucher({"kind": "FIXED", "code": "HETHAN", "value": 10000, "valid_until": "2026-01-02"})
        self.clock.advance(days=5)
        with self.assertRaisesRegex(ValidationError, "hết hạn"):
            self.store.vouchers.validate("HETHAN", 500_000)


class CoverImageTest(BookstoreTestCase):
    PNG = make_image("PNG", (900, 1200))

    def setUp(self):
        super().setUp()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Bookstore(self.storage, clock=self.clock, media=CoverImageStore(self.folder.name))

    def files(self):
        return sorted(p.name for p in Path(self.folder.name).iterdir())

    def test_upload_replace_and_delete(self):
        first = self.store.set_cover("BK-OOP-01", "bia.png", self.PNG).cover_image
        self.assertEqual(self.files(), sorted([first, CoverImageStore.thumb_name(first)]))
        second = self.store.set_cover("BK-OOP-01", "bia-moi.png", self.PNG).cover_image
        self.assertEqual(self.files(), sorted([second, CoverImageStore.thumb_name(second)]))  # ảnh cũ được dọn
        self.store.delete_product("BK-OOP-01")
        self.assertEqual(self.files(), [])

    def test_creates_resized_webp_versions(self):
        from PIL import Image

        name = self.store.set_cover("BK-OOP-01", "bia.jpg", make_image("JPEG", (1800, 2400))).cover_image
        self.assertTrue(name.endswith(".webp"))
        folder = Path(self.folder.name)
        with Image.open(folder / name) as full, Image.open(folder / CoverImageStore.thumb_name(name)) as thumb:
            self.assertEqual((full.format, full.size), ("WEBP", (600, 800)))
            self.assertEqual(thumb.size, (240, 320))
        self.assertLess((folder / CoverImageStore.thumb_name(name)).stat().st_size, 20_000)

    def test_small_images_are_not_enlarged(self):
        from PIL import Image

        name = self.store.set_cover("BK-OOP-01", "nho.png", make_image("PNG", (150, 200))).cover_image
        with Image.open(Path(self.folder.name) / name) as full:
            self.assertEqual(full.size, (150, 200))

    def test_legacy_image_without_thumbnail_falls_back(self):
        media = self.store.media
        (Path(self.folder.name) / "cu.png").write_bytes(self.PNG)
        self.assertEqual(media.thumb_or_original("cu.png"), "cu.png")

    def test_rejects_fake_images(self):
        with self.assertRaisesRegex(ValidationError, "không phải ảnh"):
            self.store.set_cover("BK-OOP-01", "virus.png", b"<html>hack</html>")
        with self.assertRaisesRegex(ValidationError, "không phải ảnh"):  # đúng đầu file PNG nhưng hỏng
            self.store.set_cover("BK-OOP-01", "hong.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        with self.assertRaisesRegex(ValidationError, "JPG, PNG"):  # ảnh GIF thật đổi đuôi thành .png
            self.store.set_cover("BK-OOP-01", "doi-duoi.png", make_image("GIF", (50, 50)))
        with self.assertRaisesRegex(ValidationError, "JPG, PNG"):
            self.store.set_cover("BK-OOP-01", "bia.gif", b"GIF89a")
        self.assertEqual(self.store.inventory.get("BK-OOP-01").cover_image, "")


class MembershipFlowTest(BookstoreTestCase):
    def test_request_then_admin_confirm_unlocks_drive(self):
        customer = self.new_customer()
        self.assertFalse(self.store.membership.has_access(customer))
        order = self.store.request_membership(customer)
        self.assertEqual(order.order_type, OrderType.MEMBERSHIP)
        self.assertIs(self.store.request_membership(customer), order)  # không tạo yêu cầu trùng
        with self.assertRaises(AccessDeniedError):
            self.store.membership.drive_access(customer)

        self.store.complete_order(order.id)
        access = self.store.membership.drive_access(customer)
        self.assertEqual(access.folder_url, self.store.vault.folder_url)
        self.assertEqual(len(access.ebook_links), len(self.store.inventory.ebooks()))

    def test_membership_expires_after_duration(self):
        customer = self.new_customer()
        self.store.complete_order(self.store.request_membership(customer).id)
        self.clock.advance(days=self.store.vault.duration_days + 1)
        self.assertFalse(self.store.membership.has_access(customer))

    def test_cancelled_request_does_not_unlock(self):
        customer = self.new_customer()
        self.store.cancel_order(self.store.request_membership(customer).id)
        self.assertFalse(self.store.membership.has_access(customer))


class AdSupportTest(BookstoreTestCase):
    def test_view_counts_only_after_full_duration(self):
        before = self.store.ads.ledger.total_views
        session = self.store.start_ad("viewer-1")
        self.clock.advance(seconds=self.store.ads.settings.duration_seconds - 1)
        with self.assertRaises(ValidationError):
            self.store.complete_ad(session.token, "viewer-1")
        self.clock.advance(seconds=1)
        self.assertEqual(self.store.complete_ad(session.token, "viewer-1"), before + 1)
        with self.assertRaises(ValidationError):  # một phiên chỉ tính một lần
            self.store.complete_ad(session.token, "viewer-1")

    def test_ads_do_not_unlock_drive(self):
        customer = self.new_customer()
        session = self.store.start_ad(customer.id)
        self.clock.advance(seconds=60)
        self.store.complete_ad(session.token, customer.id)
        self.assertFalse(self.store.membership.has_access(customer))

    def test_token_belongs_to_viewer(self):
        session = self.store.start_ad("viewer-1")
        self.clock.advance(seconds=60)
        with self.assertRaises(ValidationError):
            self.store.complete_ad(session.token, "viewer-2")


class SqliteStorageTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "bookstore.db"

    def test_round_trip(self):
        store = Bookstore(SqliteStorage(self.path))
        self.assertEqual(Bookstore(SqliteStorage(self.path)).to_dict(), store.to_dict())

    def test_only_changed_rows_are_written(self):
        storage = SqliteStorage(self.path)
        store = Bookstore(storage)
        store.restock("BK-OOP-01", 5)
        self.assertEqual(storage.last_changes, {"inserted": 0, "updated": 1, "deleted": 0})
        store.delete_product("BK-SCI-05")
        self.assertEqual(storage.last_changes, {"inserted": 0, "updated": 0, "deleted": 1})

    def test_corrupted_database_is_reported(self):
        self.path.write_bytes(b"day khong phai sqlite" * 50)
        with self.assertRaises(DataCorruptedError):
            Bookstore(SqliteStorage(self.path))

    def test_reads_previous_data_version(self):
        data = Bookstore(InMemoryStorage()).to_dict()
        data["version"] = 3
        del data["vouchers"]
        store = Bookstore(InMemoryStorage(data))
        self.assertEqual(store.vouchers.all(), [])


class JsonStorageTest(unittest.TestCase):
    def test_corrupted_file_raises_instead_of_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text("{ không phải json", encoding="utf-8")
            with self.assertRaises(DataCorruptedError):
                Bookstore(JsonFileStorage(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "{ không phải json")

    def test_file_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            store = Bookstore(JsonFileStorage(path))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), store.to_dict())
            self.assertEqual(Bookstore(JsonFileStorage(path)).to_dict(), store.to_dict())


if __name__ == "__main__":
    unittest.main()
