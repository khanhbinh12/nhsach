"""Kiểm thử tầng web bằng Flask test client."""

import gzip
import io
import re
import tempfile
import unittest

from bookstore.models import OrderStatus
from bookstore.services import Bookstore, CoverImageStore
from bookstore.storage import InMemoryStorage
from bookstore.web import create_app
from bookstore.web.forms import ProductForm

from .helpers import FakeClock, make_image

DRIVE_FOLDER = "drive.google.com/drive/folders"


class WebTestCase(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.store = Bookstore(InMemoryStorage(), clock=self.clock)
        self.app = create_app(self.store, testing=True)
        self.client = self.app.test_client()

    def csrf(self, path="/"):
        html = self.client.get(path).get_data(as_text=True)
        match = re.search(r'name="csrf_token" value="([0-9a-f]+)"', html)
        self.assertIsNotNone(match, "Trang không có CSRF token")
        return match.group(1)

    def post(self, path, data=None, follow=False):
        payload = {"csrf_token": self.csrf(), **(data or {})}
        return self.client.post(path, data=payload, follow_redirects=follow)

    def login(self, login, password):
        return self.post("/tai-khoan/dang-nhap", {"login": login, "password": password})


class PublicPagesTest(WebTestCase):
    def test_public_pages_render(self):
        for path in ("/", "/sach/BK-OOP-01/lap-trinh-huong-doi-tuong-python-nang-cao", "/gio-hang", "/kho-ebook/", "/ung-ho/",
                     "/tai-khoan/dang-nhap", "/tai-khoan/dang-ky"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_ebook_has_no_shop_page(self):
        self.assertEqual(self.client.get("/sach/EB-001").status_code, 404)

    def test_guest_cannot_see_drive_links(self):
        html = self.client.get("/kho-ebook/").get_data(as_text=True)
        self.assertNotIn(DRIVE_FOLDER, html)
        self.assertNotIn("demo-clean-code", html)

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post("/gio-hang/them", data={"product_id": "BK-OOP-01"})
        self.assertEqual(response.status_code, 400)


class AuthorizationTest(WebTestCase):
    def test_admin_pages_require_admin(self):
        self.assertEqual(self.client.get("/quan-tri/").status_code, 302)
        self.login("quan.lh@example.com", "123456")
        self.assertEqual(self.client.get("/quan-tri/").status_code, 403)

    def test_admin_can_open_dashboard(self):
        response = self.login("admin", "admin123")
        self.assertTrue(response.headers["Location"].endswith("/quan-tri/"))
        for path in ("/quan-tri/", "/quan-tri/don-hang", "/quan-tri/sach", "/quan-tri/sach/them/physical",
                     "/quan-tri/sach/EB-001/sua", "/quan-tri/khach-hang", "/quan-tri/cau-hinh"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_wrong_password_shows_error(self):
        response = self.post("/tai-khoan/dang-nhap", {"login": "admin", "password": "sai"}, follow=True)
        self.assertIn("Sai tài khoản hoặc mật khẩu", response.get_data(as_text=True))

    def test_external_next_redirect_is_ignored(self):
        payload = {"csrf_token": self.csrf(), "login": "admin", "password": "admin123"}
        response = self.client.post("/tai-khoan/dang-nhap?next=//evil.example", data=payload)
        self.assertNotIn("evil.example", response.headers["Location"])


class ShoppingFlowTest(WebTestCase):
    def test_register_add_to_cart_and_checkout(self):
        stock_before = self.store.inventory.get("BK-OOP-01").stock
        self.post("/tai-khoan/dang-ky", {"name": "Ngọc Lan", "phone": "0966111222", "email": "lan@example.com",
                                         "password": "matkhau1", "confirm_password": "matkhau1"})
        self.post("/gio-hang/them", {"product_id": "BK-OOP-01", "quantity": "2"})
        response = self.post("/thanh-toan", {"contact_phone": "0966111222", "shipping_address": "5 Hai Bà Trưng",
                                             "payment_method": "Thanh toán khi nhận hàng (COD)"})
        self.assertEqual(response.status_code, 302)
        customer = self.store.customers.find_by_identifier("lan@example.com")
        orders = self.store.orders.by_customer(customer.id)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].status, OrderStatus.PENDING)
        self.assertEqual(self.client.get("/gio-hang").status_code, 200)
        self.assertEqual(self.store.inventory.get("BK-OOP-01").stock, stock_before - 2)

    def test_checkout_requires_login(self):
        response = self.client.get("/thanh-toan")
        self.assertIn("/tai-khoan/dang-nhap", response.headers["Location"])


class MembershipWebTest(WebTestCase):
    def test_member_sees_drive_links_after_admin_confirms(self):
        self.login("quan.lh@example.com", "123456")
        self.assertNotIn(DRIVE_FOLDER, self.client.get("/kho-ebook/").get_data(as_text=True))
        pending = self.store.membership.pending_request(self.store.customers.get("KH-REG03"))
        self.store.complete_order(pending.id)  # admin xác nhận đã nhận tiền
        self.assertIn(DRIVE_FOLDER, self.client.get("/kho-ebook/").get_data(as_text=True))

    def test_existing_member_sees_links(self):
        self.login("nam.nt@example.com", "123456")
        self.assertIn("demo-clean-code", self.client.get("/kho-ebook/").get_data(as_text=True))


class OrderAndVoucherWebTest(WebTestCase):
    def test_apply_voucher_in_cart(self):
        self.login("quan.lh@example.com", "123456")
        self.post("/gio-hang/them", {"product_id": "BK-OOP-01", "quantity": "1"})
        html = self.post("/gio-hang/ma-giam-gia", {"code": "giam30k"}, follow=True).get_data(as_text=True)
        self.assertIn("đã được áp dụng", html)
        self.post("/thanh-toan", {"contact_phone": "0905123987", "shipping_address": "1 Lê Lợi",
                                  "payment_method": "Thanh toán khi nhận hàng (COD)"})
        self.assertEqual(self.store.vouchers.get("GIAM30K").used_count, 1)

    def test_unknown_voucher_shows_error(self):
        self.post("/gio-hang/them", {"product_id": "BK-OOP-01", "quantity": "1"})
        html = self.post("/gio-hang/ma-giam-gia", {"code": "KHONGCO"}, follow=True).get_data(as_text=True)
        self.assertIn("không tồn tại", html)

    def test_admin_order_actions_follow_state(self):
        self.login("admin", "admin123")
        order = next(o for o in self.store.orders.all() if o.is_pending and o.order_type.charges_shipping)
        self.post(f"/quan-tri/don-hang/{order.id}/complete")  # chưa giao → bị từ chối
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.post(f"/quan-tri/don-hang/{order.id}/ship")
        self.assertEqual(order.status, OrderStatus.SHIPPING)
        self.post(f"/quan-tri/don-hang/{order.id}/complete")
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        response = self.client.post(f"/quan-tri/don-hang/{order.id}/bay-ba", data={"csrf_token": self.csrf()})
        self.assertEqual(response.status_code, 404)

    def test_admin_voucher_page(self):
        self.login("admin", "admin123")
        self.assertEqual(self.client.get("/quan-tri/ma-giam-gia").status_code, 200)
        self.post("/quan-tri/ma-giam-gia", {"kind": "PERCENT", "code": "SINHVIEN15", "value": "15"})
        self.assertIsNotNone(self.store.vouchers.find("SINHVIEN15"))


class CoverUploadWebTest(WebTestCase):
    PNG = make_image("PNG", (900, 1200))

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.clock = FakeClock()
        self.store = Bookstore(InMemoryStorage(), clock=self.clock, media=CoverImageStore(self.folder.name))
        self.app = create_app(self.store, testing=True)
        self.client = self.app.test_client()

    def test_upload_cover_and_serve_it(self):
        self.login("admin", "admin123")
        token = self.csrf("/quan-tri/sach/BK-OOP-01/sua")
        product_form = ProductForm.for_product(self.store.inventory.get("BK-OOP-01"))
        form = {field.name: product_form.value(field.name) for field in product_form.fields}
        form.update(csrf_token=token, cover=(io.BytesIO(self.PNG), "bia.png"))
        self.client.post("/quan-tri/sach/BK-OOP-01/sua", data=form, content_type="multipart/form-data")
        image = self.store.inventory.get("BK-OOP-01").cover_image
        self.assertTrue(image.endswith(".webp"))
        self.assertIn(image, self.client.get("/sach/BK-OOP-01", follow_redirects=True).get_data(as_text=True))  # trang chi tiết: ảnh lớn
        thumb = CoverImageStore.thumb_name(image)
        self.assertIn(thumb, self.client.get("/").get_data(as_text=True))  # danh sách: ảnh thu nhỏ
        for name in (image, thumb):
            with self.client.get(f"/anh-bia/{name}") as response:  # luôn đóng file kể cả khi kiểm tra thất bại
                self.assertEqual((response.status_code, response.mimetype), (200, "image/webp"))
        self.assertEqual(self.client.get("/anh-bia/../secret_key.txt").status_code, 404)


class PerformanceWebTest(WebTestCase):
    def test_favicon_served(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_static_assets_versioned_and_cached(self):
        html = self.client.get("/").get_data(as_text=True)
        match = re.search(r'href="(/static/style\.css\?v=[0-9a-f]{10})"', html)
        self.assertIsNotNone(match)
        response = self.client.get(match.group(1))
        self.assertGreaterEqual(response.cache_control.max_age, 30 * 24 * 3600)
        response.close()

    def test_html_is_gzipped_when_supported(self):
        plain = self.client.get("/")
        zipped = self.client.get("/", headers={"Accept-Encoding": "gzip, deflate"})
        self.assertEqual(zipped.headers.get("Content-Encoding"), "gzip")
        self.assertIn("Accept-Encoding", zipped.headers.get("Vary", ""))
        self.assertEqual(gzip.decompress(zipped.data), plain.data)
        self.assertLess(len(zipped.data), len(plain.data) / 3)
        self.assertNotIn("Content-Encoding", plain.headers)


class AdSupportWebTest(WebTestCase):
    def test_watch_ad_flow(self):
        before = self.store.ads.ledger.total_views
        self.post("/ung-ho/xem")
        self.assertEqual(self.client.get("/ung-ho/xem").status_code, 200)
        self.post("/ung-ho/hoan-tat")  # bấm quá sớm → không tính
        self.assertEqual(self.store.ads.ledger.total_views, before)
        self.clock.advance(seconds=self.store.ads.settings.duration_seconds)
        self.post("/ung-ho/hoan-tat")
        self.assertEqual(self.store.ads.ledger.total_views, before + 1)


if __name__ == "__main__":
    unittest.main()
