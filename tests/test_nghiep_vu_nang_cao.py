from datetime import date
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from flask import template_rendered

from nha_sach import create_app
from nha_sach.kho import SCHEMA, CoSoDuLieu
from nha_sach.mo_hinh import BiaSach, MaGiamGia, SoDienThoai
from tests.test_du_lieu import SACH_MAU
from nha_sach.du_lieu import doc_du_lieu_mau


class TestNghiepVuNangCao(unittest.TestCase):
    def test_mo_file_cu_va_wal(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cu.db"
            conn = sqlite3.connect(path)
            try:
                conn.executescript(SCHEMA)
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
                self.assertFalse(conn.execute("SELECT 1 FROM sqlite_master WHERE name='muc_theo_sach'").fetchone())
            finally:
                conn.close()
            app = create_app({"NHA_SACH_DB": path, "NAP_DU_LIEU_MAU": True})
            self.assertEqual(len(app.extensions["nha_sach_cua_hang"].trang_chu()["sach_moi"]), 8)
            with CoSoDuLieu(path).doc() as conn:
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 6)
                self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                self.assertEqual(conn.execute("PRAGMA synchronous").fetchone()[0], 1)
                self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 10000)
                self.assertEqual(
                    [row["name"] for row in conn.execute("PRAGMA index_info(muc_theo_sach)")],
                    ["ma_sach", "ma_don", "so_luong"],
                )
            CoSoDuLieu(path).tao_bang()

    def test_bia_mau_dat_tuong_phan_va_da_dang(self):
        du_lieu = doc_du_lieu_mau(SACH_MAU)
        khuon = set()
        for item in du_lieu["sach"]:
            bia = BiaSach.tao(item["tieu_de"], item["mau_bia"], item["danh_muc"])
            self.assertLessEqual(len(bia.dong_tieu_de), 4)
            khuon.add(bia.khuon)
            for chu in (bia.mau_chu, bia.mau_phu):
                a, b = sorted(map(BiaSach.do_sang, (chu, item["mau_bia"])))
                self.assertGreaterEqual((b + .05) / (a + .05), 4.5)
        self.assertGreaterEqual(len(khuon), 3)

    def test_bia_tu_choi_ma_danh_muc_kieu_so(self):
        with self.assertRaisesRegex(TypeError, "slug"):
            BiaSach.tao("Dế Mèn", "#123456", 4)
        self.assertEqual(BiaSach.tao("Dế Mèn", "#123456", None).khuon, "hien_dai")

    def test_khuon_bia_theo_slug_khi_ma_danh_muc_thay_doi(self):
        from nha_sach.du_lieu import nap_mau

        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db"})
            app.extensions["nha_sach_quan_ly"].luu_danh_muc("Danh mục thêm", "them-moi", 0)
            dv = app.extensions["nha_sach_cua_hang"]
            nap_mau(dv.csdl, SACH_MAU)
            sach = dv.chi_tiet_sach(1)["sach"]
            self.assertNotEqual(sach.ma_danh_muc, 4)
            self.assertEqual(sach.duong_dan_danh_muc, "thieu-nhi")
            self.assertEqual(sach.bia.khuon, "thieu_nhi")
            self.assertEqual(dv.tim_sach(q="to hoai")["ket_qua"].muc[0].bia.khuon, "thieu_nhi")

    def test_dien_thoai_va_ly_do_ma(self):
        for so in ("+84 901.234.567", "84-901-234-567", "0901234567"):
            self.assertEqual(SoDienThoai.chuan_hoa(so), "0901234567")
        self.assertIsNone(SoDienThoai.chuan_hoa("090123456"))
        hom_nay = date(2026, 11, 25)
        self.assertIn("hết hạn", MaGiamGia("A", "tien", 1, 0, date(2000, 1, 1), None, 0, True).ly_do(0, hom_nay))
        self.assertIn("hết lượt", MaGiamGia("A", "tien", 1, 0, None, 1, 1, True).ly_do(0, hom_nay))
        self.assertIn("9.000 đ", MaGiamGia("A", "tien", 1, 10000, None, None, 0, True).ly_do(1000, hom_nay))

    def test_loi_truong_flash_va_xac_nhan_huy(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            c = app.test_client()
            ma_don = app.extensions["nha_sach_quan_ly"].lay_don(16).ma_tra_cuu
            with c.session_transaction() as phien:
                phien.update(csrf="kiem", don_da_xac_minh=[ma_don])
            c.post("/quan-ly/dang-nhap", data={"csrf": "kiem", "mat_khau": "admin"})
            with c.session_transaction() as phien:
                phien["csrf"] = "kiem"
            ket_qua = []
            def ghi(sender, template, context):
                ket_qua.append(context)
            with template_rendered.connected_to(ghi, app):
                def post(path, **du_lieu):
                    return c.post(path, data=dict(du_lieu, csrf="kiem"))
                post("/dang-ky", ho_ten="An", email="an@example.invalid", dien_thoai="090123456")
                self.assertIn("dien_thoai", ket_qua[-1]["loi_truong"])
                post("/tra-cuu", ma="ABCD1234", dien_thoai="090123456")
                self.assertIn("dien_thoai", ket_qua[-1]["loi_truong"])
                post("/tra-cuu", ma="ABCD1234", dien_thoai="0901234567")
                self.assertEqual(ket_qua[-1]["loi_truong"], {})
                post("/quan-ly/sach/moi", tieu_de="Sách", tac_gia="Tác giả", gia="abc")
                self.assertIn("Giá bán", ket_qua[-1]["loi_truong"]["gia"])
                self.assertEqual(post(f"/don/{ma_don}/huy").status_code, 400)
                self.assertEqual(post("/quan-ly/don/16/trang-thai", trang_thai="da_huy").status_code, 400)
                self.assertEqual(post(f"/don/{ma_don}/huy", xac_nhan="1").status_code, 302)
                self.assertEqual(post("/gio/them", ma=1, so_luong=1).status_code, 302)
                with c.session_transaction() as phien:
                    self.assertIn('/gio', str(phien["_flashes"][-1][1]))
                c.get("/dat-hang")
                ma_thao_tac = ket_qua[-1]["ma_thao_tac"]
                self.assertEqual(ket_qua[-1]["gio"].con_thieu_mien_phi, 245000)
                form = dict(ho_ten="An", dia_chi="Huế", phuong_thuc="cod", ma_thao_tac=ma_thao_tac)
                self.assertEqual(post("/dat-hang", **form, dien_thoai="090123456").status_code, 400)
                self.assertIn("dien_thoai", ket_qua[-1]["loi_truong"])
                self.assertEqual(post("/dat-hang", **form, dien_thoai="+84 901 234 567").status_code, 302)
                with c.session_transaction() as phien:
                    self.assertIn("lưu mã tra cứu", str(phien["_flashes"][-1][1]))


    def test_r1_giu_nguyen_don_khi_ma_vua_mat_hieu_luc(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            c = app.test_client()
            c.get("/dat-hang")
            with c.session_transaction() as ss:
                ma = ss["ma_thao_tac_dat_hang"]
                csrf = ss["csrf"]
                ss.update(gio={"1": 2}, ma_giam_gia="CHAOHE")
            ql = app.extensions["nha_sach_quan_ly"]
            ql.bat_tat_ma("CHAOHE")
            r = c.post("/dat-hang", data=dict(
                csrf=csrf, ma_thao_tac=ma, ho_ten="An", dien_thoai="0901234567",
                dia_chi="Huế", phuong_thuc="cod",
            ))
            self.assertEqual(r.status_code, 400)
            self.assertIn("không hoạt động", r.get_data(as_text=True))
            self.assertEqual(ql.danh_sach_don(None, 1)["ket_qua"].tong, 18)

    def test_r2_gui_lai_form_them_sach_chi_tao_mot_sach(self):
        from werkzeug.datastructures import MultiDict
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            ql = app.extensions["nha_sach_quan_ly"]
            form = MultiDict(dict(tieu_de="Thử", tac_gia="An", gia="1000", gia_bia="1000",
                                  ton_kho="1", ma_danh_muc="1", ma_thao_tac="thu-them-sach-000001"))
            sach, da_luu = ql.luu_sach(form)
            self.assertTrue(da_luu)
            lai, da_luu = ql.luu_sach(form)
            self.assertFalse(da_luu)
            self.assertEqual(lai.ma, sach.ma)

    def test_r3_huy_don_loai_danh_gia_khoi_sach(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            dv = app.extensions["nha_sach_cua_hang"]
            ql = app.extensions["nha_sach_quan_ly"]
            k = dv.dang_ky("An", "an@example.invalid", "0901234567", "mat-khau", "mat-khau")
            don = dv.dat_hang(
                {1: 1}, dict(ho_ten="An", dien_thoai="0901234567", dia_chi="Huế", phuong_thuc="cod"),
                "kiem-thu-huy-don-000001", ma_khach=k.ma,
            )
            truoc = dv.chi_tiet_sach(1)["sach"].so_danh_gia
            dv.luu_danh_gia(1, k.ma, 1, "Đánh giá tạm")
            self.assertEqual(dv.chi_tiet_sach(1)["sach"].so_danh_gia, truoc + 1)
            ql.doi_trang_thai(don.ma, "da_huy")
            chi_tiet = dv.chi_tiet_sach(1)
            self.assertEqual(chi_tiet["sach"].so_danh_gia, truoc)
            self.assertNotIn("Đánh giá tạm", [x["danh_gia"].noi_dung for x in chi_tiet["danh_gia"]])


    def test_headers_va_gioi_han_dang_nhap(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            c = app.test_client()
            r = c.get("/")
            for ten, gia_tri in {
                "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                "Referrer-Policy": "same-origin",
            }.items():
                self.assertEqual(r.headers.get(ten), gia_tri)
            with c.session_transaction() as ss:
                csrf = ss["csrf"]
            for path in ("/dang-nhap", "/quan-ly/dang-nhap"):
                for _ in range(5):
                    self.assertEqual(c.post(path, data=dict(csrf=csrf, mat_khau="sai")).status_code, 200)
                self.assertEqual(c.post(path, data=dict(csrf=csrf, mat_khau="sai")).status_code, 429)

    def test_don_cod_mau_va_phi_giao(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            don = app.extensions["nha_sach_quan_ly"].lay_don(1)
            self.assertTrue(don.da_thanh_toan)
            self.assertEqual(don.trang_thai.value, "hoan_thanh")
            self.assertEqual(don.tong, don.tam_tinh - don.giam_gia + don.phi_giao)


    def test_csv_dung_nhan_va_doanh_thu_theo_thang(self):
        import csv
        from io import StringIO
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            c = app.test_client()
            with c.session_transaction() as ss:
                ss["csrf"] = "kiem-csv"
            c.post("/quan-ly/dang-nhap", data={"csrf": "kiem-csv", "mat_khau": "admin"})
            rows = list(csv.reader(StringIO(c.get("/quan-ly/xuat/don.csv").data.decode("utf-8-sig"))))
            self.assertIn("Hoàn thành", {row[4] for row in rows[1:]})
            self.assertTrue(all(row[5] == "Trả tiền khi nhận hàng" for row in rows[1:]))
            self.assertRegex(rows[1][10], r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")
            self.assertEqual(rows[1][2], '="0900000000"')
            doanh_thu = c.get("/quan-ly/xuat/doanh-thu.csv").data.decode("utf-8-sig")
            self.assertIn("Tháng,Doanh thu", doanh_thu)
            _, theo_thang = doanh_thu.split("Tháng,Doanh thu", 1)
            tong_quan = app.extensions["nha_sach_quan_ly"].tong_quan()
            thang = {row[0]: int(row[1]) for row in csv.reader(StringIO(theo_thang)) if row}
            self.assertEqual(thang, {row["thang"]: row["tien"] for row in tong_quan["doanh_thu_thang"] if row["tien"]})

    def test_khoa_bi_mat_doc_lai(self):
        from app import khoa_bi_mat
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "instance" / "khoa_bi_mat"
            lan_dau = khoa_bi_mat(file)
            self.assertGreaterEqual(len(lan_dau), 32)
            self.assertEqual(khoa_bi_mat(file), lan_dau)


    def test_quyen_huy_csrf_va_sach_ngung_ban(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            guest = app.test_client()
            guest.get("/")
            with guest.session_transaction() as ss:
                csrf = ss["csrf"]
            for gui in ({}, {"csrf": "sai"}):
                self.assertEqual(guest.post("/gio/them", data=dict(gui, ma=1)).status_code, 400)
            ql = app.extensions["nha_sach_quan_ly"]
            don = ql.lay_don(16)
            huy = guest.post(f"/don/{don.ma_tra_cuu}/huy", data=dict(csrf=csrf, xac_nhan=1))
            self.assertEqual(huy.location, f"/tra-cuu?ma={don.ma_tra_cuu}")
            self.assertEqual(ql.lay_don(don.ma).trang_thai.value, "cho_xac_nhan")
            guest.post("/gio/them", data=dict(csrf=csrf, ma=1))
            ql.xoa_sach(1)
            with template_rendered.connected_to(self.ghi_template, app):
                self.ngu_canh = []
                guest.get("/gio")
                self.assertEqual(self.ngu_canh[-1]["gio"].muc, [])
                self.assertTrue(self.ngu_canh[-1]["gio"].canh_bao)
            with guest.session_transaction() as ss:
                self.assertEqual(ss["gio"], {})

    def ghi_template(self, sender, template, context):
        self.ngu_canh.append(context)

    def test_loi_413_va_500_dung_template(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "MAX_CONTENT_LENGTH": 256})
            @app.get("/kiem-500")
            def kem():
                from flask import abort
                abort(500)
            c = app.test_client()
            self.ngu_canh = []
            with template_rendered.connected_to(self.ghi_template, app):
                self.assertEqual(c.post("/gio/them", data={"ma": "1" * 500}).status_code, 413)
                self.assertEqual(self.ngu_canh[-1]["ma_loi"], 413)
                self.assertEqual(c.get("/kiem-500").status_code, 500)
                self.assertEqual(self.ngu_canh[-1]["ma_loi"], 500)

    def test_dang_xuat_vo_hieu_nonce_va_tra_cuu_gioi_han(self):
        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            c = app.test_client()
            c.get("/quan-ly/dang-nhap")
            with c.session_transaction() as ss:
                token = ss["csrf"]
            self.assertEqual(c.post("/quan-ly/dang-nhap", data={"csrf": token, "mat_khau": "admin"}).status_code, 302)
            self.assertIn("Đang dùng mật khẩu mặc định", c.get("/quan-ly/").get_data(as_text=True))
            with c.session_transaction() as ss:
                nonce, token = ss["quan_ly"], ss["csrf"]
            self.assertEqual(c.post("/quan-ly/dang-xuat", data={"csrf": token}).status_code, 302)
            with c.session_transaction() as ss:
                ss["quan_ly"] = nonce
                ss["csrf"] = token
            self.assertEqual(c.get("/quan-ly/").location, "/quan-ly/dang-nhap")
            form = {"csrf": token, "ma": "ZZZZ0000", "dien_thoai": "0901111111"}
            for _ in range(5):
                self.assertEqual(c.post("/tra-cuu", data=form).status_code, 200)
            self.assertEqual(c.post("/tra-cuu", data=form).status_code, 429)
