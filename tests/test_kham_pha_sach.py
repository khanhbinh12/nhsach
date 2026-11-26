from datetime import timedelta
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from flask import template_rendered

from nha_sach import create_app


class TestKhamPhaSach(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app = create_app({"TESTING": True, "NHA_SACH_DB": Path(tmp.name) / "db",
                               "NAP_DU_LIEU_MAU": True})
        self.shop = self.app.extensions["nha_sach_cua_hang"]
        self.ql = self.app.extensions["nha_sach_quan_ly"]
        self.c = self.app.test_client()
        with self.c.session_transaction() as session:
            session["csrf"] = "kiem-viec-05"

    def get(self, url):
        captures = []

        def capture(sender, template, context):
            captures.append(context)

        with template_rendered.connected_to(capture, self.app):
            response = self.c.get(url)
        self.assertEqual(response.status_code, 200)
        return captures[-1]

    def test_lien_quan_goi_y_va_loc_tac_gia(self):
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("UPDATE sach SET tieu_de='Đồi Gió', tac_gia='Ánh Trần', gia=100000, gia_bia=120000 WHERE ma=1")
            conn.execute("UPDATE sach SET nha_xuat_ban='Đồi Gió', tac_gia='anh tran', gia=1000 WHERE ma=2")
            conn.execute("UPDATE sach SET tieu_de='Đồi Gió Cao', tac_gia='Ánh Trần', dang_ban=0 WHERE ma=3")
        tim = self.get("/sach?q=doi+gio")
        self.assertEqual([s.ma for s in tim["ket_qua"].muc][:2], [1, 2])
        self.assertEqual(self.get("/sach?q=doi+gio&sap_xep=gia_tang")["ket_qua"].muc[0].ma, 2)
        self.assertEqual(self.get("/sach?q=doi+gio&sap_xep=moi")["ket_qua"].muc[0].ma, 2)
        loc = self.get("/sach?tac_gia=anh+tran")
        self.assertEqual({s.ma for s in loc["ket_qua"].muc}, {1, 2})
        self.assertEqual(sum(m.so_sach_dang_ban for m in loc["danh_muc_kem_dem"]), 49)
        self.assertEqual(self.c.get("/api/goi-y?q=d").json, [])
        goi_y = self.c.get("/api/goi-y?q=doi+gio").json
        self.assertEqual([muc["ma"] for muc in goi_y][:2], [1, 2])
        self.assertTrue(goi_y[0]["bia"]["dong_tieu_de"])
        self.assertLessEqual(len(self.c.get("/api/goi-y?q=an").json), 6)

    def test_loc_con_hang_giam_gia_review_va_sap_xep(self):
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("DELETE FROM bai_review")
            conn.execute("UPDATE sach SET gia_bia=100000, gia=10000, ton_kho=12 WHERE ma=1")
            conn.execute("UPDATE sach SET gia_bia=100000, gia=20000, ton_kho=0 WHERE ma=2")
        bai = self.ql.tao_nhap_review(1, "Review", "Nội dung.", "Nhà sách")
        self.assertEqual(self.get("/sach?co_review=1")["ket_qua"].tong, 0)
        self.ql.doi_duyet_review(bai.ma, True)
        loc = self.get("/sach?giam_gia=1&con_hang=1&co_review=1")["ket_qua"].muc
        self.assertEqual([s.ma for s in loc if s.co_review], [1])
        self.assertEqual(self.get("/sach?sap_xep=giam_sau&giam_gia=1")["ket_qua"].muc[0].ma, 1)
        self.assertNotIn(2, [s.ma for s in self.get("/sach?con_hang=1&sap_xep=giam_sau")["ket_qua"].muc])
        diem = self.get("/sach?sap_xep=danh_gia")["ket_qua"].muc
        self.assertEqual([(s.diem_tb, s.so_danh_gia) for s in diem],
                         sorted(((s.diem_tb, s.so_danh_gia) for s in diem), reverse=True))
        self.ql.doi_duyet_review(bai.ma, False)
        self.assertEqual(self.get("/sach?co_review=1")["ket_qua"].tong, 0)

    def test_khoi_trang_chu_doanh_so_va_review(self):
        self.assertEqual(self.get("/")["ten_khoi"], "Gợi ý cho bạn")
        now = self.shop.dong_ho.bay_gio()
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("UPDATE sach SET ton_kho=10 WHERE ma BETWEEN 40 AND 50")
            for ma in range(40, 51):
                luc = now - timedelta(days=31 if ma == 49 else 1)
                conn.execute("""INSERT INTO don_hang
                    (ma,ma_tra_cuu,ho_ten,dien_thoai,dia_chi,phuong_thuc,trang_thai,
                     tam_tinh,giam_gia,phi_giao,tong,tao_luc,cap_nhat_luc,da_hoan_tien)
                    VALUES (?,?, 'A','0901234567','Hue','cod',?,1,0,0,1,?,?,?)""",
                             (ma + 100, f"kiem{ma}", "da_huy" if ma == 48 else "hoan_thanh",
                              luc.isoformat(), luc.isoformat(), ma == 50))
                conn.execute("INSERT INTO muc_don VALUES (?, ?, 'A', 1, ?)", (ma + 100, ma, ma))
        # Dùng bảy cuốn bán thật và một cuốn tiêu điểm bán thật.
        bai = self.ql.tao_nhap_review(1, "Review", "Câu thứ nhất. Câu thứ hai! Câu ba.", "Nhà sách")
        self.ql.doi_duyet_review(bai.ma, True)
        home = self.get("/")
        self.assertEqual(home["noi_bat"].ma, 47)
        self.assertEqual(home["ten_khoi"], "Gợi ý cho bạn")
        self.assertEqual([s.ma for s in home["ban_chay"] if s.so_ban_that], list(range(46, 39, -1)))
        self.assertEqual(home["goc_review"][0]["trich"], "Câu thứ nhất. Câu thứ hai!")
        self.assertEqual(len(home["tieu_diem"]), 3)
        self.assertTrue(all(s.gia < s.gia_bia and s.ton_kho for s in home["uu_dai"]))
        self.assertGreater(len({s.ma_danh_muc for s in home["sach_moi"]}), 1)
        ids = [home["noi_bat"].ma] + [m["sach"].ma for m in home["goc_review"]]
        for key in ("sach_moi", "ban_chay", "uu_dai", "tieu_diem"):
            ids += [s.ma for s in home[key]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([s.ma for s in self.get("/sach?sap_xep=ban_chay")["ket_qua"].muc],
                         list(range(47, 39, -1)))

    def test_chi_tiet_va_vua_xem_theo_phien(self):
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("UPDATE sach SET tac_gia='Ánh Trần' WHERE ma=1")
            conn.execute("UPDATE sach SET tac_gia=' anh tran ', ma_danh_muc=14 WHERE ma=2")
            conn.execute("UPDATE sach SET tac_gia='Ánh Trần', dang_ban=0 WHERE ma=3")
        for ma in (2, 4, 5, 6, 7, 8, 9, 10, 11, 1):
            detail = self.get(f"/sach/{ma}")
        self.assertEqual([s.ma for s in detail["cung_tac_gia"]], [2])
        self.assertTrue(all(s.ma not in (1, 2, 3) for s in detail["lien_quan"]))
        self.assertEqual([s.ma for s in detail["vua_xem"]], [11, 10, 9, 8, 7, 6, 5, 4])
        self.assertEqual(self.c.get("/sach/3").status_code, 404)
        self.assertEqual(self.c.head("/sach/2").status_code, 200)
        with self.c.session_transaction() as session:
            self.assertEqual(session["vua_xem"], [1, 11, 10, 9, 8, 7, 6, 5])
        with self.shop.csdl.giao_dich() as conn:
            conn.execute("UPDATE sach SET dang_ban=0 WHERE ma=11")
        self.assertEqual([s.ma for s in self.get("/")["vua_xem"]], [1, 10, 9, 8, 7, 6, 5])
        with self.app.test_client() as khac:
            khac.get("/")
            with khac.session_transaction() as session:
                self.assertNotIn("vua_xem", session)

    def test_json_gio_mua_ngay_va_ma_giam_gia_tai_dat_hang(self):
        data = {"ma": 1, "csrf": "kiem-viec-05", "tiep": "/dat-hang"}
        r = self.c.post("/gio/them", data=data, headers={"Accept": "application/json"})
        self.assertEqual(r.json, dict(ok=True, so_trong_gio=1, ten_sach=self.shop.sach_dang_ban(1).tieu_de))
        r = self.c.post("/gio/them", data=dict(data, so_luong="sai"), headers={"Accept": "application/json"})
        self.assertEqual((r.status_code, r.json["ok"], r.json["so_trong_gio"]), (400, False, 1))
        self.assertEqual(self.c.post("/gio/them", data=data).location, "/dat-hang")
        self.assertEqual(self.c.post("/gio/them", data=dict(data, tiep="//vi-du.invalid")).location, "/gio")
        ma = self.get("/dat-hang")["ma_thao_tac"]
        form = dict(csrf="kiem-viec-05", ma_thao_tac=ma, ma_giam_gia="sai", ho_ten="An",
                    dien_thoai="0901234567", dia_chi="Huế", phuong_thuc="cod")
        self.assertEqual(self.c.post("/dat-hang", data=form).status_code, 400)
        r = self.c.post("/dat-hang", data=dict(form, ma_giam_gia="chaohe"))
        self.assertEqual(r.status_code, 302)
        don = self.shop.lay_don(r.location.rsplit("/", 1)[-1])
        self.assertEqual(don.ma_giam_gia, "CHAOHE")
        self.assertGreater(don.giam_gia, 0)

    def test_ngan_sach_sql(self):
        base_connect = sqlite3.connect
        sql = []

        def connect(*args, **kwargs):
            conn = base_connect(*args, **kwargs)
            conn.set_trace_callback(sql.append)
            return conn

        self.get("/sach/2")
        self.get("/sach/3")
        with patch("nha_sach.kho.sqlite3.connect", connect):
            for url, expected in (("/", 4), ("/sach/1", 7), ("/sach?q=de+men", 4), ("/api/goi-y?q=de+men", 1)):
                with self.subTest(url=url):
                    sql.clear()
                    self.assertEqual(self.c.get(url).status_code, 200)
                    self.assertEqual(sum(q.lstrip().upper().startswith(("SELECT", "WITH")) for q in sql), expected)
