"""Kiểm thử ưu tiên 4: chống dò mật khẩu, header bảo mật, ghi log lỗi, đường dẫn đẹp."""

import re
import unittest
from datetime import timedelta

from bookstore.exceptions import AuthenticationError
from bookstore.models.text import slugify
from bookstore.services import Bookstore
from bookstore.services.login_throttle import LoginThrottle
from bookstore.storage import InMemoryStorage
from bookstore.web import create_app

from .helpers import FakeClock


class LoginThrottleTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.throttle = LoginThrottle(max_failures=3, window=timedelta(minutes=15),
                                      lockout=timedelta(minutes=10), clock=self.clock)

    def test_locks_after_too_many_failures_then_unlocks(self):
        for _ in range(2):
            self.assertFalse(self.throttle.record_failure("a"))
        self.assertTrue(self.throttle.record_failure("a"))
        with self.assertRaisesRegex(AuthenticationError, "10 phút"):
            self.throttle.ensure_allowed("a")
        self.throttle.ensure_allowed("b")  # khóa khác không bị ảnh hưởng
        self.clock.advance(minutes=10)
        self.throttle.ensure_allowed("a")

    def test_old_failures_expire(self):
        self.throttle.record_failure("a")
        self.throttle.record_failure("a")
        self.clock.advance(minutes=16)  # 2 lần sai cũ đã ra khỏi khung 15 phút
        self.assertFalse(self.throttle.record_failure("a"))


class BookstoreLoginLimitTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.store = Bookstore(InMemoryStorage(), clock=self.clock)

    def test_account_locked_even_with_correct_password(self):
        for _ in range(5):
            with self.assertRaises(AuthenticationError):
                self.store.authenticate("admin", "sai", "10.0.0.1")
        with self.assertRaisesRegex(AuthenticationError, "quá nhiều lần"):
            self.store.authenticate("admin", "admin123", "10.0.0.2")  # đúng mật khẩu vẫn phải chờ
        self.clock.advance(minutes=15)
        self.assertTrue(self.store.authenticate("admin", "admin123", "10.0.0.2").is_admin)

    def test_ip_limit_across_many_accounts(self):
        for i in range(20):
            with self.assertRaises(AuthenticationError):
                self.store.authenticate(f"khong-co-{i}@example.com", "sai", "10.9.9.9")
        with self.assertRaisesRegex(AuthenticationError, "quá nhiều lần"):
            self.store.authenticate("admin", "admin123", "10.9.9.9")
        self.assertTrue(self.store.authenticate("admin", "admin123", "10.0.0.5").is_admin)  # IP khác vẫn vào được

    def test_success_resets_counter(self):
        for _ in range(4):
            with self.assertRaises(AuthenticationError):
                self.store.authenticate("admin", "sai")
        self.store.authenticate("admin", "admin123")
        for _ in range(4):
            with self.assertRaises(AuthenticationError):
                self.store.authenticate("admin", "sai")
        self.assertTrue(self.store.authenticate("admin", "admin123").is_admin)


class WebHardeningTest(unittest.TestCase):
    def setUp(self):
        self.store = Bookstore(InMemoryStorage())
        self.app = create_app(self.store, testing=True)
        self.app.config["CSRF_ENABLED"] = False  # các test này kiểm tra header / log, không kiểm tra CSRF
        self.client = self.app.test_client()

    def test_security_headers(self):
        response = self.client.get("/")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp.split("script-src")[1].split(";")[0])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_no_inline_scripts_in_pages(self):
        self.client.post("/tai-khoan/dang-nhap", data={"login": "admin", "password": "admin123"})
        for path in ("/", "/quan-tri/", "/quan-tri/don-hang", "/quan-tri/sach", "/quan-tri/khach-hang",
                     "/quan-tri/ma-giam-gia", "/quan-tri/cau-hinh"):
            response = self.client.get(path)
            html = response.get_data(as_text=True)
            with self.subTest(path=path):
                self.assertEqual(response.status_code, 200)  # chắc chắn đang xem trang thật, không bị chuyển về đăng nhập
                self.assertNotRegex(html, r"<script>|<script [^>]*>[^<]+</script>| on(submit|click)=")
        self.assertIn("data-confirm=", self.client.get("/quan-tri/sach").get_data(as_text=True))

    def test_unexpected_error_is_logged_and_hidden(self):
        @self.app.get("/loi-thu")
        def boom():
            raise RuntimeError("chi tiết nội bộ không được lộ ra ngoài")

        with self.assertLogs(self.app.logger, level="ERROR") as logs:
            response = self.client.get("/loi-thu")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("chi tiết nội bộ", response.get_data(as_text=True))
        self.assertIn("/loi-thu", "\n".join(logs.output))

    def test_failed_login_is_logged(self):
        with self.assertLogs(self.app.logger, level="WARNING") as logs:
            self.client.post("/tai-khoan/dang-nhap", data={"login": "admin", "password": "sai"})
        self.assertIn("Đăng nhập thất bại", "\n".join(logs.output))


class SlugTest(unittest.TestCase):
    def test_slugify_vietnamese(self):
        self.assertEqual(slugify("Lập Trình Hướng Đối Tượng Python"), "lap-trinh-huong-doi-tuong-python")
        self.assertEqual(slugify("Đắc Nhân Tâm (Bản Đặc Biệt) – 2024!"), "dac-nhan-tam-ban-dac-biet-2024")
        self.assertEqual(slugify("???"), "sach")

    def test_old_and_wrong_urls_redirect_to_canonical(self):
        client = create_app(Bookstore(InMemoryStorage()), testing=True).test_client()
        canonical = "/sach/BK-OOP-01/lap-trinh-huong-doi-tuong-python-nang-cao"
        for old in ("/sach/BK-OOP-01", "/sach/BK-OOP-01/ten-cu"):
            with self.subTest(url=old):
                response = client.get(old)
                self.assertEqual(response.status_code, 301)
                self.assertTrue(response.headers["Location"].endswith(canonical))
        html = client.get(canonical).get_data(as_text=True)
        self.assertRegex(html, r'<link rel="canonical" href="http://localhost/sach/BK-OOP-01/lap-trinh')
        self.assertIn(canonical, client.get("/").get_data(as_text=True))  # link trong danh mục đã có tên


if __name__ == "__main__":
    unittest.main()
