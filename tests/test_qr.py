from binascii import crc_hqx
from types import SimpleNamespace
import unittest
from xml.etree import ElementTree

from nha_sach.mo_hinh import PhuongThuc, TrangThaiDon
from nha_sach.qr import noi_dung_vietqr, thong_tin_qr


class TestQr(unittest.TestCase):
    def test_payload_co_so_tien_ma_don_va_crc(self):
        payload = noi_dung_vietqr("970436", "123456789", 120000, "NHASACH D0000001")
        self.assertIn("5406120000", payload)
        self.assertIn("NHASACH D0000001", payload)
        self.assertEqual(payload[-4:], f"{crc_hqx(payload[:-4].encode('ascii'), 0xffff):04X}")

    def test_svg_demo_va_khong_hien_sau_khi_huy(self):
        don = SimpleNamespace(
            phuong_thuc=PhuongThuc.CHUYEN_KHOAN, trang_thai=TrangThaiDon.CHO_XAC_NHAN,
            da_thanh_toan=False, ma_tra_cuu="D0000001", tong=120000,
        )
        svg, thong_tin = thong_tin_qr(don, {})
        self.assertTrue(ElementTree.fromstring(svg).tag.endswith("svg"))
        self.assertIn("Mô phỏng", thong_tin["ten"])
        don.trang_thai = TrangThaiDon.DA_HUY
        self.assertEqual(thong_tin_qr(don, {}), (None, None))
