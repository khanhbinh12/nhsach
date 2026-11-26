from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from jinja2 import DictLoader, StrictUndefined

from nha_sach import create_app


class TestWebKhach(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app = create_app({
            "TESTING": True, "NHA_SACH_DB": Path(tmp.name) / "test.db", "NAP_DU_LIEU_MAU": True,
        })
        self.app.jinja_env.undefined = StrictUndefined
        self.app.jinja_loader = DictLoader({
            "trang_chu.html": "{{ sach_moi|length }}|{{ danh_muc|length }}|{{ noi_bat.tieu_de }}|{{ csrf }}",
            "danh_sach.html": "{{ ket_qua.tong }}|{{ ket_qua.muc[0].tieu_de }}",
            "chi_tiet.html": "{{ sach.tieu_de }}|{{ danh_muc_sach.ten }}",
            "dat_hang.html": '<input name="ma_thao_tac" value="{{ ma_thao_tac }}">',
            "gio_hang.html": "{{ gio.ma_giam_gia.ma if gio.ma_giam_gia else 'khong-co-ma' }}",
            "tra_cuu.html": "{{ loi or '' }}",
            "don_hang.html": "{{ don.muc[0].tieu_de }}|{{ co_the_huy }}",
        })
        self.khach = self.app.test_client()

    def test_trang_chu_va_tim_khong_dau(self):
        trang = self.khach.get("/").get_data(as_text=True)
        self.assertTrue(trang.startswith("8|14|"))
        ket_qua = self.khach.get("/sach?q=to+hoai").get_data(as_text=True)
        self.assertIn("Dế Mèn phiêu lưu ký", ket_qua)
        chi_tiet = self.khach.get("/sach/1").get_data(as_text=True)
        self.assertIn("Dế Mèn phiêu lưu ký", chi_tiet)

    def test_hai_post_cung_form_va_tra_cuu(self):
        self.assertEqual(self.khach.post("/gio/them", data={"ma": 1}).status_code, 400)
        with self.khach.session_transaction() as ss:
            csrf = ss["csrf"]
        ton_truoc = self.app.extensions["nha_sach_cua_hang"].chi_tiet_sach(1)["sach"].ton_kho
        self.khach.post("/gio/them", data={"ma": 1, "so_luong": 2, "csrf": csrf})
        html = self.khach.get("/dat-hang").get_data(as_text=True)
        ma = re.search(r'name="ma_thao_tac" value="([^"]+)"', html).group(1)
        form = dict(
            csrf=csrf, ma_thao_tac=ma, ho_ten="An", dien_thoai="0901234567",
            dia_chi="Hue", phuong_thuc="cod", ghi_chu="",
        )
        lan_1, lan_2 = [self.khach.post("/dat-hang", data=form) for _ in range(2)]
        self.assertEqual(lan_1.status_code, 302)
        self.assertEqual(lan_1.location, lan_2.location)
        self.assertEqual(self.khach.get(lan_1.location).status_code, 200)
        cua_hang = self.app.extensions["nha_sach_cua_hang"]
        self.assertEqual(cua_hang.chi_tiet_sach(1)["sach"].ton_kho, ton_truoc - 2)

        khach_khac = self.app.test_client()
        self.assertEqual(khach_khac.get(lan_1.location).location,
                         "/tra-cuu?ma=" + lan_1.location.rsplit("/", 1)[-1])
        with khach_khac.session_transaction() as ss:
            csrf_khac = ss["csrf"]
        xac_minh = khach_khac.post("/tra-cuu", data={
            "csrf": csrf_khac, "ma": lan_1.location.rsplit("/", 1)[-1], "dien_thoai": "0901234567",
        })
        self.assertEqual(xac_minh.location, lan_1.location)

    def test_dat_hang_sau_khi_giam_gio_duoi_muc_ap_ma(self):
        self.khach.get("/")
        with self.khach.session_transaction() as ss:
            csrf = ss["csrf"]
        self.khach.post("/gio/them", data=dict(csrf=csrf, ma=1, so_luong=2))
        self.khach.post("/gio/ma-giam-gia", data=dict(csrf=csrf, ma_giam_gia="CHAOHE"))
        with self.khach.session_transaction() as ss:
            self.assertEqual(ss["ma_giam_gia"], "CHAOHE")
        self.khach.post("/gio/sua", data=dict(csrf=csrf, ma=1, so_luong=1))
        self.assertEqual(self.khach.get("/gio").get_data(as_text=True), "khong-co-ma")
        html = self.khach.get("/dat-hang").get_data(as_text=True)
        ma = re.search(r'name="ma_thao_tac" value="([^"]+)"', html).group(1)
        resp = self.khach.post("/dat-hang", data=dict(
            csrf=csrf, ma_thao_tac=ma, ho_ten="An", dien_thoai="0901234567",
            dia_chi="Hue", phuong_thuc="cod",
        ))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.startswith("/don/"))
        don = self.app.extensions["nha_sach_cua_hang"].lay_don(resp.location.rsplit("/", 1)[-1])
        self.assertIsNone(don.ma_giam_gia)
        self.assertEqual((don.tam_tinh, don.giam_gia, don.tong), (55000, 0, 80000))
        with self.khach.session_transaction() as ss:
            self.assertNotIn("ma_giam_gia", ss)
