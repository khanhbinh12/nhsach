from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from flask import template_rendered

from app import khoa_bi_mat
from nha_sach import create_app
from nha_sach.kho import KhoMaGiamGia


class TestHoanThien(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)
        self.app = create_app({"TESTING": True, "NHA_SACH_DB": self.path / "db",
                               "NAP_DU_LIEU_MAU": True})
        self.c = self.app.test_client()
        self.shop = self.app.extensions["nha_sach_cua_hang"]
        with self.c.session_transaction() as ss:
            ss["csrf"] = "kiem-viec-06"

    def post(self, url, **data):
        return self.c.post(url, data={"csrf": "kiem-viec-06", **data})

    def test_ap_bo_ma_giu_form_va_khong_tao_don(self):
        self.post("/gio/them", ma=1, so_luong=2)
        form = dict(ho_ten="Khach Thu", dien_thoai="0901234567", dia_chi="Hue",
                    ghi_chu="Giao buoi sang", phuong_thuc="chuyen_khoan")
        with self.shop.csdl.doc() as conn:
            truoc = conn.execute("SELECT COUNT(*) FROM don_hang").fetchone()[0]
        for action, code, status, discount in (
            ("ap_ma", "CHAOHE", 200, 11000), ("bo_ma", "CHAOHE", 200, 0),
            ("ap_ma", "SAI", 400, 0),
        ):
            with self.subTest(action=action, code=code):
                ctx = []
                def capture(sender, template, context):
                    ctx.append(context)
                with template_rendered.connected_to(capture, self.app):
                    resp = self.post("/dat-hang", hanh_dong=action, ma_giam_gia=code, **form)
                self.assertEqual(resp.status_code, status)
                self.assertEqual(ctx[-1]["mac_dinh"], form)
                self.assertEqual(ctx[-1]["gio"].giam_gia, discount)
                self.assertEqual("ma_giam_gia" in ctx[-1]["loi_truong"], code == "SAI")
        with self.shop.csdl.doc() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM don_hang").fetchone()[0], truoc)

    def test_sales_detail_and_ranking_agree(self):
        luc = self.shop.dong_ho.bay_gio().isoformat()
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("UPDATE don_hang SET ghi_chu='', cap_nhat_luc=? WHERE ma=1", (luc,))
            conn.execute("DELETE FROM thao_tac_dat_hang WHERE ma_don=1")
            ma, qty = conn.execute("SELECT ma_sach,so_luong FROM muc_don WHERE ma_don=1").fetchone()
        self.assertEqual(self.shop.tim_sach(sap_xep="ban_chay")["ket_qua"].muc[0].so_ban_that, qty)
        self.assertEqual(self.shop.chi_tiet_sach(ma)["sach"].so_ban_that, qty)

    def test_danh_sach_ma_chi_mot_select(self):
        sql = []
        with self.shop.csdl.doc() as conn:
            conn.set_trace_callback(sql.append)
            self.assertGreater(len(KhoMaGiamGia(conn).danh_sach()), 1)
        self.assertEqual(len(sql), 1)

    def test_khoa_bi_mat_dong_thoi_khong_can_hard_link(self):
        path = self.path / "instance" / "key"
        with patch("os.link", side_effect=PermissionError), ThreadPoolExecutor(max_workers=8) as pool:
            keys = list(pool.map(khoa_bi_mat, [path] * 16))
        self.assertEqual(set(keys), {path.read_text(encoding="ascii")})
        self.assertGreaterEqual(len(keys[0]), 48)

    def test_review_mau_va_hero_demo(self):
        with self.shop.csdl.doc() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM bai_review").fetchone()[0], 20)
            self.assertEqual(conn.execute(
                """SELECT COUNT(*),COUNT(DISTINCT s.ma_danh_muc)
                   FROM bai_review r JOIN sach s ON s.ma=r.ma_sach WHERE r.trang_thai='da_duyet'"""
            ).fetchone()[:], (6, 6))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sach WHERE trim(mo_ta)=''").fetchone()[0], 0)
            self.assertIsNotNone(conn.execute("SELECT 1 FROM sach WHERE tac_gia='Hans Christian Andersen'").fetchone())
        home = self.shop.trang_chu()
        self.assertTrue(home["noi_bat"].co_review)
        self.assertTrue(home["noi_bat"].anh_bia)
        self.assertNotEqual(home["noi_bat"].duong_dan_danh_muc, "trinh-tham-kinh-di")
        self.assertTrue(home["goc_review"])

    def test_csdl_cu_bo_sung_review_va_giu_bai_da_chinh(self):
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("UPDATE bai_review SET noi_dung='Ban da bien tap' WHERE ma_sach=31")
            conn.execute("DELETE FROM bai_review WHERE ma_sach<>31")
            conn.execute("UPDATE sach SET mo_ta='' WHERE tieu_de='Chất Michelle'")
            conn.execute("PRAGMA user_version = 5")
        for _ in range(2):
            self.shop.csdl.tao_bang()
        with self.shop.csdl.doc() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 6)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM bai_review").fetchone()[0], 20)
            self.assertEqual(conn.execute("SELECT noi_dung FROM bai_review WHERE ma_sach=31").fetchone()[0],
                             "Ban da bien tap")
            self.assertTrue(conn.execute("SELECT mo_ta FROM sach WHERE tieu_de='Chất Michelle'").fetchone()[0])

    def test_tao_review_web(self):
        self.assertEqual(self.c.get("/quan-ly/review/moi").status_code, 302)
        self.post("/quan-ly/dang-nhap", mat_khau="admin")
        with self.c.session_transaction() as ss:
            ss["csrf"] = "kiem-viec-06"
        self.assertEqual(self.c.get("/quan-ly/review/moi?ma_sach=1").status_code, 200)
        self.assertEqual(self.post("/quan-ly/review/moi", ma_sach=1).status_code, 400)
        form = dict(ma_sach=1, tieu_de="Tieu de", noi_dung="Noi dung", tac_gia_review="Nha sach")
        self.assertEqual(self.post("/quan-ly/review/moi", **form).status_code, 302)
        self.assertEqual(self.post("/quan-ly/review/moi", **form).status_code, 400)
        with self.shop.csdl.doc() as conn:
            self.assertEqual(conn.execute("SELECT trang_thai FROM bai_review WHERE ma_sach=1").fetchone()[0], "nhap")
