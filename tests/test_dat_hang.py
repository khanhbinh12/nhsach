from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nha_sach.dich_vu import DichVuCuaHang, DichVuQuanLy
from nha_sach.kho import CoSoDuLieu, KhoMaGiamGia, KhoSach
from nha_sach.loi import HetHang, LoiNghiepVu
from nha_sach.mo_hinh import TrangThaiDon


class TestDatHang(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = CoSoDuLieu(Path(tmp.name) / "test.db")
        self.db.tao_bang()
        with self.db.giao_dich() as conn:
            conn.execute("INSERT INTO danh_muc VALUES (1, 'Van hoc', 'van-hoc', 1)")
            conn.execute("""INSERT INTO sach
                (ma, tieu_de, tac_gia, gia, gia_bia, ton_kho, ma_danh_muc, mau_bia, ngay_them)
                VALUES (1, 'Sach', 'Tac gia', 150000, 150000, 2, 1, '#333333', '2026-11-24')""")
            conn.executemany("INSERT INTO ma_giam_gia VALUES (?, 'tien', 1000, ?, ?, ?, ?, 1)", [
                ("CON1", 0, None, 1, 0),
                ("HETLUOT", 0, None, 1, 1),
                ("HETHAN", 0, "2000-01-01", None, 0),
                ("TOITHIEU", 200000, None, None, 0),
            ])
        self.cua_hang = DichVuCuaHang(self.db)
        self.quan_ly = DichVuQuanLy(self.db)
        self.thong_tin = dict(ho_ten="An", dien_thoai="090.123.4567", dia_chi="Hue", phuong_thuc="cod")
        self.ma_thao_tac = "ma-thao-tac-dat-hang-001"

    def ton_va_luot(self):
        with self.db.doc() as conn:
            return KhoSach(conn).lay(1).ton_kho, KhoMaGiamGia(conn).lay("CON1").da_dung

    def test_gui_lai_va_huy_chi_ap_mot_lan(self):
        don = self.cua_hang.dat_hang({1: 2}, self.thong_tin, self.ma_thao_tac, "CON1")
        don_gui_lai = self.cua_hang.dat_hang({}, {}, self.ma_thao_tac)
        self.assertEqual(don.ma, don_gui_lai.ma)
        self.assertEqual((don.tam_tinh, don.giam_gia, don.phi_giao), (300000, 1000, 25000))
        self.assertEqual(self.ton_va_luot(), (0, 1))
        self.assertEqual(self.cua_hang.tra_cuu(don.ma_tra_cuu, "0901234567").ma, don.ma)
        self.assertIsNone(self.cua_hang.tra_cuu(don.ma_tra_cuu, "0900000000"))
        self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DA_HUY, khach_huy=True)
        with self.assertRaises(LoiNghiepVu):
            self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DA_HUY, khach_huy=True)
        self.assertEqual(self.ton_va_luot(), (2, 0))

    def test_ma_khong_hop_le_va_qua_ton_khong_ghi(self):
        for ma in ("HETHAN", "HETLUOT", "TOITHIEU"):
            with self.subTest(ma=ma), self.assertRaises(LoiNghiepVu):
                self.cua_hang.dat_hang({1: 1}, self.thong_tin, self.ma_thao_tac, ma)
        with self.assertRaises(HetHang):
            self.cua_hang.dat_hang({1: 3}, self.thong_tin, self.ma_thao_tac)
        self.assertEqual(self.ton_va_luot(), (2, 0))
        self.assertEqual(self.cua_hang.xem_gio({1: 2}).phi_giao, 0)

    def test_khong_giao_don_chua_chuyen_khoan(self):
        thong_tin = dict(self.thong_tin, phuong_thuc="chuyen_khoan")
        don = self.cua_hang.dat_hang({1: 1}, thong_tin, self.ma_thao_tac)
        self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DANG_CHUAN_BI)
        with self.assertRaises(LoiNghiepVu):
            self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DANG_GIAO)

    def test_don_da_thanh_toan_can_xac_nhan_hoan_tien(self):
        thong_tin = dict(self.thong_tin, phuong_thuc="chuyen_khoan")
        don = self.cua_hang.dat_hang({1: 1}, thong_tin, self.ma_thao_tac)
        self.assertTrue(self.quan_ly.xac_nhan_thanh_toan(don.ma).da_thanh_toan)
        with self.assertRaises(LoiNghiepVu):
            self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DA_HUY, khach_huy=True)
        with self.assertRaises(LoiNghiepVu):
            self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DA_HUY)
        self.assertEqual(self.ton_va_luot(), (1, 0))
        huy = self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.DA_HUY, da_hoan_tien=True)
        self.assertTrue(huy.da_hoan_tien)
        self.assertEqual(self.ton_va_luot(), (2, 0))


    def test_cod_hoan_thanh_dong_thoi_da_thanh_toan(self):
        don = self.cua_hang.dat_hang({1: 1}, self.thong_tin, self.ma_thao_tac)
        for trang_thai in (TrangThaiDon.DANG_CHUAN_BI, TrangThaiDon.DANG_GIAO):
            don = self.quan_ly.doi_trang_thai(don.ma, trang_thai)
            self.assertFalse(don.da_thanh_toan)
        self.quan_ly.doi_trang_thai(don.ma, TrangThaiDon.HOAN_THANH)
        don = self.quan_ly.lay_don(don.ma)
        self.assertEqual(don.trang_thai, TrangThaiDon.HOAN_THANH)
        self.assertTrue(don.da_thanh_toan)
