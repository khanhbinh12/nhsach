import ast
from pathlib import Path
import re
import unittest


class TestKienTruc(unittest.TestCase):
    def test_import_va_cau_sql_dung_tang(self):
        thu_muc = Path(__file__).resolve().parents[1] / "nha_sach"
        bat_dau_sql = re.compile(
            r"^\s*(?:SELECT\s|UPDATE\s+(?:OR\s+\w+\s+)?\w+\s+SET|"
            r"INSERT\s+(?:OR\s+\w+\s+)?INTO|DELETE\s+FROM|CREATE\s+TABLE|"
            r"BEGIN\s+IMMEDIATE|WITH\s+(?:RECURSIVE\s+)?\w+\s+(?:AS\s*)?\()",
            re.IGNORECASE,
        )
        for tep in thu_muc.glob("*.py"):
            if tep.name == "kho.py":
                continue
            for nut in ast.walk(ast.parse(tep.read_text(encoding="utf-8"))):
                if isinstance(nut, ast.Import):
                    modules = {ten.name for ten in nut.names}
                elif isinstance(nut, ast.ImportFrom):
                    modules = {nut.module or "", *(ten.name for ten in nut.names)}
                else:
                    modules = set()
                with self.subTest(tep=tep.name, dong=getattr(nut, "lineno", None)):
                    modules = {ten.split(".")[-1] for ten in modules}
                    self.assertNotIn("sqlite3", modules)
                    if tep.name.startswith("web"):
                        self.assertNotIn("kho", modules)
                        self.assertNotIn("TrangThaiDon", modules)
                        if isinstance(nut, ast.Name):
                            self.assertNotEqual(nut.id, "TrangThaiDon")
                    if tep.name in {"mo_hinh.py", "dich_vu.py"}:
                        self.assertNotIn("flask", modules)
                    if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
                        self.assertIsNone(bat_dau_sql.match(nut.value))
                    if isinstance(nut, ast.JoinedStr):
                        dau = "".join(x.value if isinstance(x, ast.Constant) else "_" for x in nut.values)
                        self.assertIsNone(bat_dau_sql.match(dau))
                    if isinstance(nut, ast.Constant) and tep.name != "mo_hinh.py":
                        self.assertNotIn(nut.value, (25000, 300000))

    def test_kich_thuoc_ham_lop_va_dong_ho(self):
        thu_muc = Path(__file__).resolve().parents[1] / "nha_sach"
        for tep in thu_muc.glob("*.py"):
            cay = ast.parse(tep.read_text(encoding="utf-8"))
            for nut in ast.walk(cay):
                with self.subTest(tep=tep.name, dong=getattr(nut, "lineno", None)):
                    if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        bat_dau = min([nut.lineno, *(x.lineno for x in nut.decorator_list)])
                        self.assertLessEqual(nut.end_lineno - bat_dau + 1, 40 if nut.name == "create_app" else 60)
                    if isinstance(nut, ast.ClassDef):
                        cong_khai = [x.name for x in nut.body
                                     if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                                     and not x.name.startswith("_")]
                        self.assertLessEqual(len(cong_khai), 10, cong_khai)
                    if tep.stem.startswith("dich_vu") and isinstance(nut, ast.Call):
                        if isinstance(nut.func, ast.Attribute):
                            self.assertNotIn(ast.unparse(nut.func), {"date.today", "datetime.now"})

    def test_kho_tra_kieu_du_lieu_va_loc_doanh_thu(self):
        from dataclasses import is_dataclass
        from datetime import date
        from tempfile import TemporaryDirectory

        from nha_sach import create_app
        from nha_sach.kho import KhoBaoCaoDon, KhoDanhGia, KhoDanhMuc, KhoDonHang, KhoKhachHang

        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            quan_ly = app.extensions["nha_sach_quan_ly"]
            with quan_ly.csdl.doc() as conn:
                self.assertTrue(is_dataclass(KhoDonHang(conn).danh_sach().muc[0]))
                self.assertTrue(is_dataclass(KhoDanhMuc(conn).danh_sach()[0]))
                self.assertTrue(is_dataclass(KhoDanhMuc(conn).danh_sach_kem_dem_sach()[0]))
                self.assertTrue(is_dataclass(KhoKhachHang(conn).danh_sach()[0]))
                self.assertTrue(is_dataclass(KhoDanhGia(conn).danh_sach()[0]))
                self.assertTrue(is_dataclass(KhoDanhGia(conn).cua_sach(2)[0]))
                self.assertTrue(is_dataclass(KhoBaoCaoDon(conn).xuat_don()[0]))
                self.assertTrue(is_dataclass(KhoBaoCaoDon(conn).doanh_thu()[0]))
                self.assertEqual(KhoBaoCaoDon(conn).doanh_thu(date.max), [])
                self.assertEqual(KhoKhachHang(conn).dem(), len(KhoKhachHang(conn).danh_sach()))
                chi_muc = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
                self.assertTrue({"don_theo_luc", "sach_theo_danh_muc"} <= chi_muc)

    def test_trang_quan_ly_khong_tang_truy_van_theo_so_dong(self):
        import sqlite3
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from flask import template_rendered
        from nha_sach import create_app

        with TemporaryDirectory() as tmp:
            app = create_app({"NHA_SACH_DB": Path(tmp) / "test.db", "NAP_DU_LIEU_MAU": True})
            client = app.test_client()
            with client.session_transaction() as ss:
                ss["csrf"] = "kiem-sql"
            client.post("/quan-ly/dang-nhap", data={"csrf": "kiem-sql", "mat_khau": "admin"})
            base_connect = sqlite3.connect
            sql = []
            render = {}

            def connect(*args, **kwargs):
                conn = base_connect(*args, **kwargs)
                conn.set_trace_callback(sql.append)
                return conn

            def da_render(sender, template, context):
                render.update(context)

            def dem():
                ket_qua = []
                for path in ("/quan-ly/danh-gia", "/quan-ly/don"):
                    sql.clear()
                    render.clear()
                    with patch("nha_sach.kho.sqlite3.connect", connect):
                        self.assertEqual(client.get(path).status_code, 200)
                    # Đếm truy vấn dữ liệu, bỏ PRAGMA cấu hình mỗi kết nối.
                    ket_qua.append(sum(s.lstrip().upper().startswith(("SELECT", "WITH")) for s in sql))
                return ket_qua

            with template_rendered.connected_to(da_render, app):
                truoc = dem()
                quan_ly = app.extensions["nha_sach_quan_ly"]
                with quan_ly.csdl.giao_dich() as conn:
                    conn.execute("""WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i<40)
                        INSERT INTO khach_hang(ma,ho_ten,email,dien_thoai,mat_khau_bam,ngay_tao)
                        SELECT 100+i,'An','sql-'||i||'@example.invalid','0900000000','x','2026-11-25'
                        FROM n""")
                    conn.execute("""INSERT INTO danh_gia(ma_sach,ma_khach,so_sao,noi_dung,tao_luc)
                        SELECT 1,ma,4,'Kiểm','2026-11-25' FROM khach_hang WHERE ma>100""")
                    conn.execute("""INSERT INTO don_hang
                        (ma_tra_cuu,ho_ten,dien_thoai,dia_chi,phuong_thuc,trang_thai,
                         tam_tinh,giam_gia,phi_giao,tong,tao_luc,cap_nhat_luc)
                        SELECT 'SQL'||ma,'An','0900000000','Huế','cod','cho_xac_nhan',
                               1,0,0,1,'2030-01-01','2030-01-01' FROM khach_hang WHERE ma>100""")
                sau = dem()
                self.assertGreater(render["ket_qua"].tong, 40)
                self.assertEqual(sau, truoc)
                self.assertTrue(all(so <= 5 for so in sau), sau)

    def test_hai_cay_da_hinh_nghiep_vu(self):
        thu_muc = Path(__file__).resolve().parents[1] / "nha_sach"
        cay = [ast.parse(tep.read_text(encoding="utf-8")) for tep in thu_muc.glob("*.py")]
        lop = {nut.name: nut for module in cay for nut in module.body if isinstance(nut, ast.ClassDef)}
        truu_tuong = {
            ten for ten, nut in lop.items()
            if any(ast.unparse(goc) in {"ABC", "abc.ABC"} for goc in nut.bases)
            and any(
                ast.unparse(decorator) in {"abstractmethod", "abc.abstractmethod"}
                for ham in nut.body if isinstance(ham, (ast.FunctionDef, ast.AsyncFunctionDef))
                for decorator in ham.decorator_list
            )
        }
        tuong_ung = {
            ten: {con for con, nut in lop.items() if any(ast.unparse(goc) == ten for goc in nut.bases)}
            for ten in truu_tuong
        }
        self.assertGreaterEqual(sum(len(con) >= 2 for con in tuong_ung.values()), 2, tuong_ung)

    def test_khong_re_nhanh_theo_kieu_thanh_toan_hay_giam_gia(self):
        thu_muc = Path(__file__).resolve().parents[1] / "nha_sach"
        for ten in ("mo_hinh.py", "dich_vu.py"):
            cay = ast.parse((thu_muc / ten).read_text(encoding="utf-8"))
            for nut in ast.walk(cay):
                if not isinstance(nut, ast.Compare):
                    continue
                with self.subTest(tep=ten, dong=nut.lineno):
                    for bieu_thuc in (nut.left, *nut.comparators):
                        if isinstance(bieu_thuc, ast.Attribute):
                            self.assertNotEqual(ast.unparse(bieu_thuc.value), "PhuongThuc")
                            self.assertNotEqual(bieu_thuc.attr, "kieu")
                        if isinstance(bieu_thuc, ast.Name):
                            self.assertNotEqual(bieu_thuc.id, "kieu")
                        if isinstance(bieu_thuc, ast.Subscript) and isinstance(bieu_thuc.slice, ast.Constant):
                            self.assertNotEqual(bieu_thuc.slice.value, "kieu")
