from datetime import date
import unittest

from nha_sach.mo_hinh import (
    GiamPhanTram, GiamSoTien, MaGiamGia, PhuongThuc, ThanhToanChuyenKhoan, ThanhToanCOD, chinh_sach_thanh_toan,
)


class TestThanhToanDaHinh(unittest.TestCase):
    def test_cod_giao_truoc_va_thu_tien_khi_hoan_thanh(self):
        cod = ThanhToanCOD()
        self.assertTrue(cod.duoc_giao(False))
        self.assertFalse(cod.can_qr())
        self.assertTrue(cod.thanh_toan_khi_hoan_thanh(False))
        self.assertFalse(cod.can_hoan_tien_khi_huy(False))

    def test_chuyen_khoan_can_tra_truoc_va_co_qr(self):
        chuyen = ThanhToanChuyenKhoan()
        self.assertFalse(chuyen.duoc_giao(False))
        self.assertTrue(chuyen.duoc_giao(True))
        self.assertTrue(chuyen.can_qr())
        self.assertFalse(chuyen.thanh_toan_khi_hoan_thanh(False))
        self.assertTrue(chuyen.can_hoan_tien_khi_huy(True))

    def test_cung_loi_goi_qua_hai_chinh_sach(self):
        ket_qua = [
            (chinh_sach.duoc_giao(False), chinh_sach.can_qr())
            for chinh_sach in map(chinh_sach_thanh_toan, PhuongThuc)
        ]
        self.assertEqual(ket_qua, [(True, False), (False, True)])


class TestGiamGiaDaHinh(unittest.TestCase):
    def test_phan_tram_lay_phan_nguyen_va_gioi_han_ty_le(self):
        quy_tac = GiamPhanTram()
        self.assertEqual(quy_tac.tinh_giam(333, 10), 33)
        self.assertTrue(quy_tac.gia_tri_hop_le(100))
        self.assertFalse(quy_tac.gia_tri_hop_le(101))

    def test_so_tien_khong_phu_thuoc_tam_tinh(self):
        quy_tac = GiamSoTien()
        self.assertEqual(quy_tac.tinh_giam(333, 250), 250)
        self.assertTrue(quy_tac.gia_tri_hop_le(101))
        self.assertFalse(quy_tac.gia_tri_hop_le(0))

    def test_cung_loi_goi_tren_hai_loai_ma(self):
        ma = [
            MaGiamGia("TEST", kieu, gia_tri, 0, None, None, 0, True)
            for kieu, gia_tri in (("phan_tram", 10), ("tien", 250))
        ]
        self.assertEqual([item.tinh_giam(200, date(2026, 11, 25)) for item in ma], [20, 200])
