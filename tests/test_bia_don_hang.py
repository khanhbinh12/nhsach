from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from flask import template_rendered

from nha_sach import create_app
from nha_sach.mo_hinh import MucDon


class TestBiaDonHang(unittest.TestCase):
    def test_bia_giong_nhau_o_chi_tiet_gio_va_hai_trang_don(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"TESTING": True, "NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            khach, quan_ly = app.test_client(), app.test_client()
            ngucanh = {}

            def ghi(sender, template, context):
                ngucanh.update(context)

            with template_rendered.connected_to(ghi, app):
                chi_tiet = khach.get("/sach/1")
                sach = ngucanh["sach"]
                with khach.session_transaction() as ss:
                    csrf = ss["csrf"]
                khach.post("/gio/them", data={"csrf": csrf, "ma": 1})
                gio = khach.get("/gio")
                self.assertEqual(ngucanh["gio"].muc[0].sach.bia, sach.bia)
                khach.get("/dat-hang")
                r = khach.post("/dat-hang", data={
                    "csrf": csrf, "ma_thao_tac": ngucanh["ma_thao_tac"], "ho_ten": "An",
                    "dien_thoai": "0901234567", "dia_chi": "Huế", "phuong_thuc": "cod",
                })
                self.assertEqual(r.status_code, 302)
                don_khach = khach.get(r.location)
                don = ngucanh["don"]

                quan_ly.get("/quan-ly/dang-nhap")
                with quan_ly.session_transaction() as ss:
                    csrf = ss["csrf"]
                quan_ly.post("/quan-ly/dang-nhap", data={"csrf": csrf, "mat_khau": "admin"})
                don_quan_ly = quan_ly.get(f"/quan-ly/don/{don.ma}")

                bia = re.compile(r'<svg[^>]+aria-label="Bìa sách Dế Mèn phiêu lưu ký[^"]*"[^>]*>.*?'
                                 r'<rect width="240" height="360" fill="(#[0-9a-f]+)"', re.S)
                for trang in (chi_tiet, gio, don_khach, don_quan_ly):
                    self.assertEqual(trang.status_code, 200)
                    match = bia.search(trang.get_data(as_text=True))
                    self.assertIsNotNone(match)
                    self.assertEqual(match.group(1), sach.mau_bia)
                self.assertEqual(don.muc[0].bia, sach.bia)
                self.assertEqual(ngucanh["don"].muc[0].bia, sach.bia)

    def test_muc_don_khong_con_sach_van_co_bia_du_phong(self):
        muc = MucDon(1, "Dế Mèn phiêu lưu ký", 55000, 1)
        self.assertEqual(muc.bia.khuon, "hien_dai")
        self.assertIsNone(muc.anh_bia)
