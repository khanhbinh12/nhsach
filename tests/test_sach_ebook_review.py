import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from jinja2 import ChoiceLoader, DictLoader, StrictUndefined

from nha_sach import create_app
from nha_sach.du_lieu import nap_mau
from nha_sach.loi import LoiNghiepVu
from nha_sach.mo_hinh import TrangThaiReview
from tests.test_du_lieu import SACH_MAU
from tools.nhap_review import doc_tep
from tools.trich_ebook import EbookEpub


class TestSachEbookVaReview(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.app = create_app({"TESTING": True, "NHA_SACH_DB": self.tmp / "db", "NAP_DU_LIEU_MAU": True})
        self.shop = self.app.extensions["nha_sach_cua_hang"]
        self.ql = self.app.extensions["nha_sach_quan_ly"]
        self.c = self.app.test_client()
        self.sach = self.shop.tim_sach(q="Chất Michelle")["ket_qua"].muc[0]
        # Các ca tạo và duyệt review cần bắt đầu với danh mục review rỗng.
        with self.ql.csdl.giao_dich() as conn:
            conn.execute("DELETE FROM bai_review")

    def post(self, path, **du_lieu):
        with self.c.session_transaction() as ss:
            csrf = ss.setdefault("csrf", "kiem-viec-04")
        return self.c.post(path, data=dict(du_lieu, csrf=csrf))

    def test_review_phai_duoc_duyet_moi_hien(self):
        mau = {"tieu_de": "Tiêu đề", "noi_dung": "Nội dung thử", "tac_gia_review": "Nhà sách"}
        bai = self.ql.tao_nhap_review(self.sach.ma, **mau)
        self.assertIsNone(self.shop.chi_tiet_sach(self.sach.ma)["bai_review"])
        self.assertEqual(self.post(f"/quan-ly/review/{bai.ma}/duyet").location, "/quan-ly/dang-nhap")
        self.post("/quan-ly/dang-nhap", mat_khau="admin")
        self.app.jinja_env.undefined = StrictUndefined
        self.app.jinja_loader = ChoiceLoader([DictLoader({
            "quan_ly/review.html": "{{ loc }}|{{ bai_review[0].tieu_de }}",
            "quan_ly/sua_review.html": "{{ bai_review.tieu_de }}|{{ form|length }}",
        }), self.app.jinja_loader])
        self.assertEqual(self.c.get("/quan-ly/review?trang_thai=nhap").get_data(as_text=True), "nhap|Tiêu đề")
        self.assertEqual(self.c.get(f"/quan-ly/review/{bai.ma}/sua").status_code, 200)
        self.assertEqual(self.post(f"/quan-ly/review/{bai.ma}/duyet").status_code, 302)
        hien = self.shop.chi_tiet_sach(self.sach.ma)["bai_review"]
        self.assertEqual(hien.trang_thai, TrangThaiReview.DA_DUYET)
        self.assertIsNotNone(hien.duyet_luc)
        self.post(f"/quan-ly/review/{bai.ma}/sua", **dict(mau, noi_dung="Mới sửa"))
        self.assertIsNone(self.shop.chi_tiet_sach(self.sach.ma)["bai_review"])
        self.post(f"/quan-ly/review/{bai.ma}/duyet")
        self.post(f"/quan-ly/review/{bai.ma}/bo-duyet")
        self.assertIsNone(self.shop.chi_tiet_sach(self.sach.ma)["bai_review"])

    def test_sach_ebook_van_can_mua_truoc_khi_danh_gia(self):
        khach = self.shop.dang_ky("An", "an@example.invalid", "0901234567", "kiem-thu", "kiem-thu")
        with self.assertRaises(LoiNghiepVu):
            self.shop.luu_danh_gia(self.sach.ma, khach.ma, 5, "Thử")
        self.shop.dat_hang(
            {self.sach.ma: 1}, dict(ho_ten="An", dien_thoai="0901234567", dia_chi="Huế", phuong_thuc="cod"),
            "kiem-ebook-dat-hang-0001", ma_khach=khach.ma,
        )
        self.shop.luu_danh_gia(self.sach.ma, khach.ma, 5, "Đã đọc")
        self.assertEqual(self.shop.chi_tiet_sach(self.sach.ma)["danh_gia"][0]["danh_gia"].so_sao, 5)

    def test_chi_phuc_vu_bia_va_bo_sung_vao_csdl_cu(self):
        with self.c.get(self.sach.anh_bia) as anh:
            self.assertEqual(anh.status_code, 200)
            self.assertTrue(anh.mimetype.startswith("image/"))
        self.assertEqual(self.c.get("/bia-ebook/ebook_trich.json").status_code, 404)
        du_lieu = json.loads(SACH_MAU.read_text(encoding="utf8"))
        du_lieu["sach"] = [sach for sach in du_lieu["sach"] if not sach.get("ebook_mau")]
        du_lieu["danh_muc"] = du_lieu["danh_muc"][:8]
        cu = self.tmp / "cu.json"
        cu.write_text(json.dumps(du_lieu), encoding="utf8")
        app = create_app({"NHA_SACH_DB": self.tmp / "cu.db"})
        csdl = app.extensions["nha_sach_cua_hang"].csdl
        self.assertTrue(nap_mau(csdl, cu))
        self.assertTrue(nap_mau(csdl, SACH_MAU))
        self.assertFalse(nap_mau(csdl, SACH_MAU))
        ql = app.extensions["nha_sach_quan_ly"]
        self.assertEqual(ql.danh_sach_sach()["ket_qua"].tong, 50)
        self.assertEqual(ql.danh_sach_don(None, 1)["ket_qua"].tong, 18)

    def test_review_quan_ly_hien_sach_va_loi_form(self):
        self.post("/quan-ly/dang-nhap", mat_khau="admin")
        bai = self.ql.tao_nhap_review(self.sach.ma, "Title", "Text", "Author")
        sua = f"/quan-ly/review/{bai.ma}/sua"
        for url in ("/quan-ly/review", sua):
            with self.subTest(url=url):
                trang = self.c.get(url)
                self.assertEqual(trang.status_code, 200)
                for gia_tri in (self.sach.tieu_de, self.sach.tac_gia, self.sach.anh_bia):
                    self.assertIn(gia_tri, trang.get_data(as_text=True))
        loi = self.post(sua, tieu_de=" ", noi_dung="x" * 20001, tac_gia_review="Author")
        self.assertEqual(loi.status_code, 400)
        for ma in ("loi-rv-tieu-de", "loi-rv-noi-dung"):
            self.assertIn(f'id="{ma}"', loi.get_data(as_text=True))
        self.assertEqual(self.ql.xem_review(bai.ma).noi_dung, "Text")

    def test_doi_duong_dan_bia_trong_csdl_v4(self):
        csdl = self.ql.csdl
        with csdl.giao_dich() as conn:
            conn.execute("PRAGMA user_version = 4")
            conn.execute("UPDATE sach SET anh_bia = ? WHERE anh_bia = ?",
                         ("/bia-ebook/mui-vang.png", "/bia-ebook/mui-vang.jpg"))
            self.assertEqual(conn.execute("SELECT changes()").fetchone()[0], 1)
        csdl.tao_bang()
        with csdl.doc() as conn:
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM sach WHERE anh_bia = '/bia-ebook/mui-vang.jpg'"
            ).fetchone()[0], 1)
        with self.c.get("/bia-ebook/mui-vang.jpg") as anh:
            self.assertEqual(anh.status_code, 200)

    def test_kich_thuoc_bia_ebook(self):
        from PIL import Image

        thu_muc = SACH_MAU.parent / "bia"
        cac_bia = list(thu_muc.iterdir())
        self.assertTrue(cac_bia)
        for tep in cac_bia:
            with self.subTest(tep=tep.name), Image.open(tep) as anh:
                self.assertEqual(anh.format, "JPEG")
                self.assertLessEqual(anh.width, 600)
                self.assertLessEqual(tep.stat().st_size, 300_000)

    def test_nhap_json_va_markdown_chi_tao_nhap(self):
        file = self.tmp / "a.json"
        file.write_text(json.dumps({"reviews": [dict(ma_sach=self.sach.ma, tieu_de="T", noi_dung="N")]}), encoding="utf8")
        self.assertEqual(self.ql.nhap_review(doc_tep(file))[0].trang_thai, TrangThaiReview.NHAP)
        file = self.tmp / "b.md"
        file.write_text("## Bài 2\nSách: Dế Mèn phiêu lưu ký\n\nNội dung.", encoding="utf8")
        bai = self.ql.nhap_review(doc_tep(file))[0]
        self.assertEqual((bai.ma_sach, bai.trang_thai), (1, TrangThaiReview.NHAP))
        with self.assertRaises(LoiNghiepVu):
            self.ql.nhap_review([dict(ma_sach=2, tieu_de="T", noi_dung="N", tac_gia_review="A"), *doc_tep(file)])
        self.assertEqual(len(self.ql.danh_sach_review()), 2)

    def test_trich_epub_theo_spine_bo_qua_bia_va_muc_luc(self):
        thu_muc = self.tmp / "Tham Khảo"
        thu_muc.mkdir()
        tep = thu_muc / "test.epub"
        with ZipFile(tep, "w") as z:
            z.writestr("META-INF/container.xml", '<container><rootfile full-path="OPS/book.opf"/></container>')
            z.writestr("OPS/book.opf", """
                <package><metadata><title>Tên thử</title><creator>An</creator><publisher>NXB</publisher></metadata>
                <manifest><item id="bia" href="b.jpg" properties="cover-image" media-type="image/jpeg"/>
                <item id="toc" href="toc.xhtml" properties="nav"/><item id="p" href="p.xhtml"/></manifest>
                <spine><itemref idref="toc"/><itemref idref="p"/></spine></package>""")
            z.writestr("OPS/b.jpg", bytes.fromhex("ffd8ff"))
            z.writestr("OPS/toc.xhtml", "<html><body><p>MỤC LỤC</p></body></html>")
            z.writestr("OPS/p.xhtml", "<html><body><p>" + "thử " * 1600 + "</p></body></html>")
        sach, cover = EbookEpub(tep).doc()
        self.assertEqual((sach["title"], sach["creator"], sach["publisher"]), ("Tên thử", "An", "NXB"))
        self.assertEqual(len(sach["trich"].split()), 1500)
        self.assertNotIn("MỤC LỤC", sach["trich"])
        self.assertEqual(cover[0], ".jpg")
