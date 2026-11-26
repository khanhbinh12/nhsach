from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit
import unittest

from flask import template_rendered

from nha_sach import create_app
from nha_sach.loi import LoiNghiepVu
from tests.test_du_lieu import SACH_MAU
from nha_sach.du_lieu import doc_du_lieu_mau


class TestSuaDiemYeu(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app = create_app({"TESTING": True, "NHA_SACH_DB": Path(tmp.name) / "db", "NAP_DU_LIEU_MAU": True})
        self.shop = self.app.extensions["nha_sach_cua_hang"]
        self.ql = self.app.extensions["nha_sach_quan_ly"]
        self.c = self.app.test_client()
        self.ngu_canh = {}
        signal = template_rendered.connected_to(self._ghi, self.app)
        signal.__enter__()
        self.addCleanup(signal.__exit__, None, None, None)

    def _ghi(self, sender, template, context):
        self.ngu_canh = context

    def post(self, url, **du_lieu):
        with self.c.session_transaction() as ss:
            token = ss.setdefault("csrf", "kiem-sua-diem-yeu")
        return self.c.post(url, data=dict(du_lieu, csrf=token))

    def test_tim_ca_nha_xuat_ban(self):
        self.c.get("/sach?q=Kim+Dong")
        sach = self.ngu_canh["ket_qua"].muc
        self.assertGreaterEqual(len(sach), 3)
        self.assertTrue(all("Kim Đồng" in item.nha_xuat_ban for item in sach))

    def test_ho_so_va_dia_chi_dat_hang_gan_nhat(self):
        khach = self.shop.dang_ky("An", "an@example.invalid", "0901234567", "kiem-thu", "kiem-thu")
        with self.c.session_transaction() as ss:
            ss["ma_khach"] = khach.ma
        don = self.shop.dat_hang(
            {1: 1}, dict(ho_ten="An", dien_thoai="0901234567", dia_chi="99 Lê Lợi", phuong_thuc="cod"),
            "kiem-ho-so-dat-hang-001", ma_khach=khach.ma,
        )
        self.c.get("/dat-hang")
        self.assertEqual(self.ngu_canh["mac_dinh"]["dia_chi"], "99 Lê Lợi")
        r = self.post("/tai-khoan/ho-so", ho_ten="An mới", dien_thoai="090123456", dia_chi="Đà Nẵng")
        self.assertEqual(r.status_code, 400)
        self.assertIn("dien_thoai", self.ngu_canh["loi_truong"])
        r = self.post("/tai-khoan/ho-so", ho_ten="An mới", dien_thoai="+84 912 345 678", dia_chi="Đà Nẵng")
        self.assertEqual(r.location, "/tai-khoan")
        self.c.get("/tai-khoan")
        self.assertEqual(self.ngu_canh["ho_so"]["dien_thoai"], "0912345678")
        self.assertEqual(self.ngu_canh["ho_so"]["dia_chi"], "Đà Nẵng")
        self.assertEqual(self.ql.lay_don(don.ma).dia_chi, "99 Lê Lợi")

    def test_dem_danh_muc_co_sach_ngung_ban(self):
        ma = self.ql.lay_sach(1).ma_danh_muc
        self.ql.xoa_sach(1)
        muc = next(m for m in self.ql.danh_muc() if m["danh_muc"].ma == ma)
        self.assertEqual(muc["so_sach"], muc["so_sach_dang_ban"] + 1)
        with self.assertRaises(LoiNghiepVu):
            self.ql.xoa_danh_muc(ma)

    def test_loc_quan_ly_sach_va_tim_don(self):
        self.post("/quan-ly/dang-nhap", mat_khau="admin")
        self.ql.xoa_sach(1)
        self.c.get("/quan-ly/sach?loc=ngung_ban")
        self.assertEqual([s.ma for s in self.ngu_canh["ket_qua"].muc], [1])
        self.c.get("/quan-ly/sach?loc=sap_het")
        self.assertTrue(self.ngu_canh["ket_qua"].muc)
        self.assertTrue(all(s.dang_ban and s.ton_kho <= 5 for s in self.ngu_canh["ket_qua"].muc))
        don = self.ql.lay_don(1)
        for q in (don.ma_tra_cuu.lower(), don.ho_ten, "090.000.0000"):
            self.c.get("/quan-ly/don", query_string={"q": q})
            self.assertEqual(self.ngu_canh["q"], q)
            self.assertTrue(self.ngu_canh["ket_qua"].muc)

    def test_ngung_va_mo_ban_la_hai_hanh_dong(self):
        self.post("/quan-ly/dang-nhap", mat_khau="admin")
        for url, dang_ban, flash in (("ngung-ban", False, "Đã ngừng bán"), ("mo-ban", True, "Đã mở bán lại")):
            self.assertEqual(self.post(f"/quan-ly/sach/1/{url}").status_code, 302)
            self.assertEqual(self.ql.lay_sach(1).dang_ban, dang_ban)
            with self.c.session_transaction() as ss:
                self.assertIn(flash, ss["_flashes"][-1][1])

    def test_hero_khong_lap_trong_hai_nhom(self):
        trang = self.shop.trang_chu()
        for ten in ("sach_moi", "ban_chay"):
            self.assertNotIn(trang["noi_bat"].ma, [s.ma for s in trang[ten]])
            self.assertEqual(len(trang[ten]), 8)

    def test_dang_nhap_tro_lai_sach_can_danh_gia(self):
        r = self.post("/sach/1/danh-gia")
        self.assertEqual(parse_qs(urlsplit(r.location).query), {"tiep": ["/sach/1"]})

    def test_du_lieu_mau_mat_biec(self):
        sach = next(s for s in doc_du_lieu_mau(SACH_MAU)["sach"] if s["tieu_de"] == "Mắt biếc")
        self.assertIn("Hà Lan", sach["mo_ta"])
        self.assertIn("làng Đo Đo", sach["mo_ta"])
