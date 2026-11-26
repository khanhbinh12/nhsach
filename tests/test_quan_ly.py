from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nha_sach import create_app
from nha_sach.loi import LoiNghiepVu


class TestQuanLy(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.uploads = Path(tmp.name) / "uploads"
        self.app = create_app({
            "TESTING": True, "NHA_SACH_DB": Path(tmp.name) / "test.db",
            "THU_MUC_ANH": self.uploads, "NAP_DU_LIEU_MAU": True,
        })
        self.cua_hang = self.app.extensions["nha_sach_cua_hang"]
        self.quan_ly = self.app.extensions["nha_sach_quan_ly"]
        self.khach = self.app.test_client()
        self.admin = self.app.test_client()

    def post(self, client, path, data):
        with client.session_transaction() as phien:
            csrf = phien.setdefault("csrf", "kiem-thu")
        return client.post(path, data=dict(data, csrf=csrf))

    def dang_nhap_quan_ly(self):
        xuat = "/quan-ly/xuat/doanh-thu.csv"
        self.assertEqual(self.admin.get(xuat).location, "/quan-ly/dang-nhap")
        self.assertEqual(self.post(self.admin, "/quan-ly/dang-nhap", {"mat_khau": "admin"}).status_code, 302)

    def test_thu_muc_anh_va_gui_lai_form_sua(self):
        self.dang_nhap_quan_ly()
        sach = self.quan_ly.lay_sach(1)
        ton_truoc = sach.ton_kho
        data = dict(
            tieu_de="Tên đã sửa", tac_gia=sach.tac_gia, gia=str(sach.gia), gia_bia=str(sach.gia_bia),
            ton_kho=str(sach.ton_kho + 1), ton_kho_goc=str(sach.ton_kho), ma_danh_muc=str(sach.ma_danh_muc), dang_ban="1",
            ma_thao_tac="kiem-thu-sua-sach-0001",
        )
        for _ in range(2):
            anh = (BytesIO(b"\x89PNG\r\n\x1a\n" + b"anh-kiem-thu"), "bia.png")
            r = self.post(self.admin, "/quan-ly/sach/1/sua", dict(data, anh_bia=anh))
            self.assertEqual(r.location, "/quan-ly/sach")
        sach = self.quan_ly.lay_sach(1)
        self.assertEqual((sach.tieu_de, sach.ton_kho), ("Tên đã sửa", ton_truoc + 1))
        self.assertEqual([tep.name for tep in self.uploads.iterdir()], [sach.anh_bia.rsplit("/", 1)[-1]])

    def test_csv_va_bat_tat_ma(self):
        self.dang_nhap_quan_ly()
        for tep in ("don.csv", "doanh-thu.csv"):
            r = self.admin.get(f"/quan-ly/xuat/{tep}")
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.data.startswith(b"\xef\xbb\xbf"))
            self.assertIn(tep, r.headers["Content-Disposition"])
        self.post(self.admin, "/quan-ly/ma-giam-gia/CHAOHE/bat-tat", {})
        ma = next(ma for ma in self.quan_ly.danh_sach_ma_giam_gia() if ma.ma == "CHAOHE")
        self.assertFalse(ma.dang_bat)

    def test_khach_chi_danh_gia_khi_da_mua(self):
        form = dict(ho_ten="An", email="an@example.invalid", dien_thoai="0901234567",
                    mat_khau="mat-khau-thu", mat_khau_lai="mat-khau-thu")
        self.assertEqual(self.post(self.khach, "/dang-ky", form).location, "/tai-khoan")
        with self.khach.session_transaction() as phien:
            ma = phien["ma_khach"]
        sao = dict(so_sao=4, noi_dung="Đánh giá thử")
        self.post(self.khach, "/sach/1/danh-gia", sao)
        self.assertEqual(self.cua_hang.thong_tin_danh_gia(1, ma), (False, None))
        don = self.cua_hang.dat_hang(
            {1: 1}, dict(ho_ten="An", dien_thoai="0901234567", dia_chi="Hue", phuong_thuc="cod"),
            "ma-thao-tac-mua-sach-001", ma_khach=ma,
        )
        self.post(self.khach, "/sach/1/danh-gia", sao)
        self.assertEqual(self.cua_hang.thong_tin_danh_gia(1, ma)[1].so_sao, 4)
        self.assertEqual([item.ma for item in self.cua_hang.don_cua_khach(ma)], [don.ma])
        with self.assertRaises(LoiNghiepVu):
            self.cua_hang.luu_danh_gia(1, ma, 6, "Không hợp lệ")


    def test_sua_danh_muc_giu_ma_va_chan_trung_slug(self):
        self.dang_nhap_quan_ly()
        muc, muc_khac = [item["danh_muc"] for item in self.quan_ly.danh_muc()[:2]]
        du_lieu = dict(ma=muc.ma, ten="Văn học đổi tên", duong_dan="van-hoc-moi", thu_tu=0)
        self.assertEqual(self.post(self.admin, "/quan-ly/danh-muc", du_lieu).status_code, 302)
        self.post(self.admin, "/quan-ly/danh-muc", dict(du_lieu, duong_dan=muc_khac.duong_dan))
        danh_muc = {item["danh_muc"].ma: item["danh_muc"] for item in self.quan_ly.danh_muc()}
        self.assertEqual(len(danh_muc), 14)
        self.assertEqual(danh_muc[muc.ma].duong_dan, "van-hoc-moi")
        self.assertEqual(danh_muc[muc.ma].ten, "Văn học đổi tên")
        self.assertEqual(danh_muc[muc_khac.ma].duong_dan, muc_khac.duong_dan)

    def test_moc_doanh_thu_la_chuoi_iso(self):
        tong_quan = self.quan_ly.tong_quan()
        for dong in tong_quan["doanh_thu_ngay"]:
            self.assertRegex(dong["ngay"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIsInstance(dong["tien"], int)
        for dong in tong_quan["doanh_thu_thang"]:
            self.assertRegex(dong["thang"], r"^\d{4}-\d{2}$")
            self.assertIsInstance(dong["tien"], int)
