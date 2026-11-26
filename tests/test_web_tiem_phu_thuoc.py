from types import SimpleNamespace
import unittest

from flask import url_for
from jinja2 import DictLoader

from nha_sach import create_app


class TestWebTiemPhuThuoc(unittest.TestCase):
    def test_dich_vu_gia_va_endpoint_cu(self):
        cua_hang = SimpleNamespace(
            lay_khach=lambda ma: None, danh_muc=lambda: [],
            trang_chu=lambda ma_vua_xem: {"noi_bat": "Dữ liệu từ dịch vụ giả"},
        )
        app = create_app({"NHA_SACH_DB": "khong-duoc-mo.db"}, dich_vu=(cua_hang, object()))
        app.jinja_loader = DictLoader({"trang_chu.html": "{{ noi_bat }}"})
        self.assertEqual(app.test_client().get("/").get_data(as_text=True), "Dữ liệu từ dịch vụ giả")
        with app.test_request_context():
            self.assertEqual(url_for("trang_chu"), "/")
            self.assertEqual(url_for("xem_gio"), "/gio")
            self.assertEqual(url_for("xem_don", ma_tra_cuu="ABCD1234"), "/don/ABCD1234")
        self.assertFalse(any(rule.build_only for rule in app.url_map.iter_rules()))

    def test_dich_vu_dung_dong_ho_gia(self):
        from datetime import datetime
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from nha_sach.dich_vu import tao_dich_vu

        luc = datetime(2030, 1, 2, 3, 4)
        dong_ho = SimpleNamespace(bay_gio=lambda: luc, hom_nay=luc.date)
        with TemporaryDirectory() as tmp:
            cua_hang, quan_ly = tao_dich_vu(Path(tmp) / "test.db", dong_ho)
            khach = cua_hang.dang_ky("An", "an@example.invalid", "0901234567", "kiem-thu", "kiem-thu")
            self.assertEqual(khach.ngay_tao, luc)
            self.assertEqual(quan_ly.tong_quan()["doanh_thu_ngay"][-1]["ngay"], "2030-01-02")
