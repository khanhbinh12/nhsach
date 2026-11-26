"""Schema SQLite và ranh giới giao dịch của ứng dụng."""
from contextlib import contextmanager
from dataclasses import fields
import sqlite3
import json
from pathlib import Path
from datetime import date, datetime
from secrets import choice
from string import ascii_uppercase, digits

from .mo_hinh import (
    BaiReview, DanhGia, DanhGiaCongKhai, DanhGiaQuanLy, DanhMuc, DanhMucDemSach,
    DoanhThuNgay, DonHang, DongXuatDon, KhachHang, KhachTongHop, MaGiamGia, MucDon,
    PhuongThuc, Sach, SachCuaReview, Trang, TrangThaiDon, TrangThaiReview, khoa_tim,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS danh_muc (
    ma INTEGER PRIMARY KEY,
    ten TEXT NOT NULL,
    duong_dan TEXT NOT NULL UNIQUE,
    thu_tu INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sach (
    ma INTEGER PRIMARY KEY AUTOINCREMENT,
    tieu_de TEXT NOT NULL,
    tac_gia TEXT NOT NULL,
    nha_xuat_ban TEXT,
    nam_xuat_ban INTEGER,
    so_trang INTEGER,
    gia INTEGER NOT NULL CHECK (gia >= 0),
    gia_bia INTEGER NOT NULL CHECK (gia_bia >= gia),
    ton_kho INTEGER NOT NULL CHECK (typeof(ton_kho) = 'integer' AND ton_kho >= 0),
    mo_ta TEXT NOT NULL DEFAULT '',
    ma_danh_muc INTEGER NOT NULL REFERENCES danh_muc(ma),
    anh_bia TEXT,
    mau_bia TEXT NOT NULL,
    dang_ban INTEGER NOT NULL DEFAULT 1 CHECK (dang_ban IN (0, 1)),
    ngay_them TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS khach_hang (
    ma INTEGER PRIMARY KEY,
    ho_ten TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    dien_thoai TEXT NOT NULL,
    dia_chi TEXT NOT NULL DEFAULT '',
    mat_khau_bam TEXT NOT NULL,
    ngay_tao TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ma_giam_gia (
    ma TEXT PRIMARY KEY,
    kieu TEXT NOT NULL CHECK (kieu IN ('phan_tram', 'tien')),
    gia_tri INTEGER NOT NULL CHECK (gia_tri >= 0),
    don_toi_thieu INTEGER NOT NULL CHECK (don_toi_thieu >= 0),
    het_han TEXT,
    so_luot_toi_da INTEGER CHECK (so_luot_toi_da >= 0),
    da_dung INTEGER NOT NULL DEFAULT 0 CHECK (da_dung >= 0),
    dang_bat INTEGER NOT NULL DEFAULT 1 CHECK (dang_bat IN (0, 1))
);
CREATE TABLE IF NOT EXISTS don_hang (
    ma INTEGER PRIMARY KEY,
    ma_tra_cuu TEXT NOT NULL UNIQUE,
    ma_khach INTEGER REFERENCES khach_hang(ma),
    ho_ten TEXT NOT NULL,
    dien_thoai TEXT NOT NULL,
    dia_chi TEXT NOT NULL,
    ghi_chu TEXT NOT NULL DEFAULT '',
    phuong_thuc TEXT NOT NULL CHECK (phuong_thuc IN ('cod', 'chuyen_khoan')),
    da_thanh_toan INTEGER NOT NULL DEFAULT 0 CHECK (da_thanh_toan IN (0, 1)),
    da_hoan_tien INTEGER NOT NULL DEFAULT 0 CHECK (da_hoan_tien IN (0, 1)),
    trang_thai TEXT NOT NULL CHECK (trang_thai IN
        ('cho_xac_nhan', 'dang_chuan_bi', 'dang_giao', 'hoan_thanh', 'da_huy')),
    tam_tinh INTEGER NOT NULL CHECK (tam_tinh >= 0),
    giam_gia INTEGER NOT NULL CHECK (giam_gia BETWEEN 0 AND tam_tinh),
    phi_giao INTEGER NOT NULL CHECK (phi_giao >= 0),
    tong INTEGER NOT NULL CHECK (tong = tam_tinh - giam_gia + phi_giao),
    ma_giam_gia TEXT REFERENCES ma_giam_gia(ma),
    tao_luc TEXT NOT NULL,
    cap_nhat_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS muc_don (
    ma_don INTEGER NOT NULL REFERENCES don_hang(ma),
    ma_sach INTEGER NOT NULL REFERENCES sach(ma),
    tieu_de TEXT NOT NULL,
    don_gia INTEGER NOT NULL CHECK (don_gia >= 0),
    so_luong INTEGER NOT NULL CHECK (so_luong > 0),
    PRIMARY KEY (ma_don, ma_sach)
);
CREATE TABLE IF NOT EXISTS danh_gia (
    ma INTEGER PRIMARY KEY,
    ma_sach INTEGER NOT NULL REFERENCES sach(ma),
    ma_khach INTEGER NOT NULL REFERENCES khach_hang(ma),
    so_sao INTEGER NOT NULL CHECK (so_sao BETWEEN 1 AND 5),
    noi_dung TEXT NOT NULL,
    tao_luc TEXT NOT NULL,
    an INTEGER NOT NULL DEFAULT 0 CHECK (an IN (0, 1)),
    UNIQUE (ma_sach, ma_khach)
);
CREATE TABLE IF NOT EXISTS thao_tac_dat_hang (
    ma TEXT PRIMARY KEY,
    ma_don INTEGER NOT NULL REFERENCES don_hang(ma)
);
CREATE TABLE IF NOT EXISTS thao_tac_sua_sach (
    ma_sach INTEGER NOT NULL REFERENCES sach(ma) ON DELETE CASCADE,
    ma TEXT NOT NULL,
    PRIMARY KEY (ma_sach, ma)
);
CREATE TABLE IF NOT EXISTS du_lieu_da_nap (ma TEXT PRIMARY KEY);
CREATE INDEX IF NOT EXISTS don_theo_khach ON don_hang(ma_khach, tao_luc);
CREATE INDEX IF NOT EXISTS don_theo_trang_thai ON don_hang(trang_thai, tao_luc);
"""


class DiChuyenLuocDo:
    BUOC = (
        (1, ("CREATE INDEX IF NOT EXISTS muc_theo_sach ON muc_don(ma_sach, ma_don, so_luong)",)),
        (2, (
            """CREATE TABLE IF NOT EXISTS thao_tac_them_sach (
                ma TEXT PRIMARY KEY,
                ma_sach INTEGER NOT NULL REFERENCES sach(ma)
            )""",
            """CREATE VIEW IF NOT EXISTS danh_gia_con_hieu_luc AS
               SELECT g.* FROM danh_gia g WHERE g.an = 0 AND EXISTS (
                   SELECT 1 FROM muc_don m JOIN don_hang h ON h.ma = m.ma_don
                   WHERE m.ma_sach = g.ma_sach AND h.ma_khach = g.ma_khach
                   AND h.trang_thai <> 'da_huy'
               )""",
        )),
        (3, (
            "CREATE INDEX IF NOT EXISTS don_theo_luc ON don_hang(tao_luc, ma)",
            "CREATE INDEX IF NOT EXISTS sach_theo_danh_muc ON sach(ma_danh_muc, dang_ban)",
        )),
        (4, (
            """CREATE TABLE IF NOT EXISTS bai_review (
                ma INTEGER PRIMARY KEY, ma_sach INTEGER NOT NULL UNIQUE REFERENCES sach(ma),
                tieu_de TEXT NOT NULL, noi_dung TEXT NOT NULL, tac_gia_review TEXT NOT NULL,
                trang_thai TEXT NOT NULL CHECK (trang_thai IN ('nhap', 'da_duyet')),
                tao_luc TEXT NOT NULL, duyet_luc TEXT
            )""",
        )),
        (5, (
            "UPDATE sach SET anh_bia = '/bia-ebook/mui-vang.jpg' WHERE anh_bia = '/bia-ebook/mui-vang.png'",
        )),
        (6, ()),
    )

    def chay(self, csdl):
        for phien_ban, cau_lenh in self.BUOC:
            with csdl.giao_dich() as conn:
                hien_tai = conn.execute("PRAGMA user_version").fetchone()[0]
                if hien_tai >= phien_ban:
                    continue
                for sql in cau_lenh:
                    conn.execute(sql)
                if phien_ban == 6:
                    self.nap_noi_dung_demo(conn)
                conn.execute(f"PRAGMA user_version = {phien_ban}")

    @staticmethod
    def nap_noi_dung_demo(conn):
        if not conn.execute("SELECT 1 FROM du_lieu_da_nap WHERE ma = 'ebook_viec04'").fetchone():
            return
        thu_muc = Path(__file__).resolve().parents[1] / "du_lieu"
        catalog = json.loads((thu_muc / "sach_mau.json").read_text(encoding="utf8"))
        conn.executemany(
            """UPDATE sach SET nam_xuat_ban = COALESCE(nam_xuat_ban, :nam_xuat_ban),
                       so_trang = COALESCE(so_trang, :so_trang),
                       mo_ta = CASE WHEN trim(mo_ta) = '' OR (tieu_de = 'Mùi Vàng'
                           AND instr(mo_ta, 'Đặc vụ Mark Girland được giao nhiệm vụ tìm và thu hồi ba bộ phim') = 1)
                           THEN :mo_ta ELSE mo_ta END
               WHERE tieu_de = :tieu_de""",
            [item for item in catalog["sach"] if item.get("ebook_mau")],
        )
        conn.execute("""UPDATE sach SET tac_gia = 'Hans Christian Andersen'
                        WHERE tieu_de = 'Công Chúa Cá' AND tac_gia = 'HansChristian Andersen'""")
        reviews = json.loads((thu_muc / "review_mau.json").read_text(encoding="utf8"))
        conn.executemany(
            """INSERT INTO bai_review (ma_sach, tieu_de, noi_dung, tac_gia_review, trang_thai, tao_luc, duyet_luc)
               SELECT min(ma), :tieu_de, :noi_dung, :tac_gia_review, :trang_thai, min(ngay_them),
                      CASE WHEN :trang_thai = 'da_duyet' THEN min(ngay_them) END
               FROM sach WHERE tieu_de = :tieu_de_sach HAVING COUNT(*) = 1
               ON CONFLICT(ma_sach) DO UPDATE SET trang_thai = excluded.trang_thai, duyet_luc = excluded.duyet_luc
               WHERE bai_review.trang_thai = 'nhap' AND excluded.trang_thai = 'da_duyet'
                 AND bai_review.tieu_de = excluded.tieu_de AND bai_review.noi_dung = excluded.noi_dung
                 AND bai_review.tac_gia_review = excluded.tac_gia_review""",
            reviews,
        )


class CoSoDuLieu:
    def __init__(self, duong_dan):
        self.duong_dan = duong_dan

    @contextmanager
    def doc(self):
        conn = sqlite3.connect(self.duong_dan, isolation_level=None, timeout=10)
        try:
            conn.row_factory = sqlite3.Row
            conn.create_function('khoa_tim', 1, khoa_tim)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA synchronous = NORMAL")
            yield conn
        finally:
            conn.close()

    def tao_bang(self):
        with self.doc() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
        DiChuyenLuocDo().chay(self)

    @contextmanager
    def giao_dich(self):
        with self.doc() as conn:
            # Khóa giao dịch ghi trước khi đọc tồn và lượt giảm giá.
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise


class KhoThaoTacSach:
    def __init__(self, conn):
        self.conn = conn

    def ma_sach_theo_thao_tac_them(self, ma):
        row = self.conn.execute("SELECT ma_sach FROM thao_tac_them_sach WHERE ma = ?", (ma,)).fetchone()
        return row["ma_sach"] if row else None

    def ghi_nhan_them(self, ma, ma_sach):
        self.conn.execute("INSERT INTO thao_tac_them_sach VALUES (?, ?)", (ma, ma_sach))

    def ghi_nhan_sua(self, ma_sach, ma):
        return self.conn.execute(
            "INSERT OR IGNORE INTO thao_tac_sua_sach VALUES (?, ?)", (ma_sach, ma),
        ).rowcount == 1


class KhoSach:
    def __init__(self, conn):
        self.conn = conn

    def tru_ton(self, ma, so_luong):
        if so_luong < 1:
            raise ValueError("Số lượng phải từ 1 trở lên.")
        return self.conn.execute(
            """UPDATE sach SET ton_kho = ton_kho - ?
               WHERE ma = ? AND dang_ban = 1 AND ton_kho >= ?""",
            (so_luong, ma, so_luong),
        ).rowcount == 1

    def doi_ton(self, ma, chenh_lech):
        return self.conn.execute(
            """UPDATE sach SET ton_kho = ton_kho + ?
               WHERE ma = ? AND ton_kho + ? >= 0""",
            (chenh_lech, ma, chenh_lech),
        ).rowcount == 1


    def tim(self, *, q="", danh_muc="", gia_tu=None, gia_den=None,
            sap_xep=None, trang=1, moi_trang=12, dang_ban=True, loai_tru=None, loc="",
            tac_gia="", giam_gia=False, con_hang=False, co_review=False, chi_goi_y=False,
            ky_doanh_so=None):
        where = [
            "(? = 0 OR s.dang_ban = 1)",
            "(? = '' OR d.duong_dan = ?)",
            "(? IS NULL OR s.gia >= ?)",
            "(? IS NULL OR s.gia <= ?)",
            "(? IS NULL OR s.ma <> ?)",
            "(? <> 'sap_het' OR (s.dang_ban = 1 AND s.ton_kho <= 5))",
            "(? <> 'ngung_ban' OR s.dang_ban = 0)",
            "(? = '' OR khoa_tim(trim(s.tac_gia)) = ?)",
            "(? = 0 OR s.gia < s.gia_bia)",
            "(? = 0 OR s.ton_kho > 0)",
            "(? = 0 OR " + self._CO_REVIEW + ")",
            """(? = '' OR instr(khoa_tim(s.tieu_de), ?) > 0
                       OR instr(khoa_tim(s.tac_gia), ?) > 0
                       OR instr(khoa_tim(COALESCE(s.nha_xuat_ban, '')), ?) > 0)""",
        ]
        q = khoa_tim(q.strip())
        tac_gia = khoa_tim(tac_gia.strip())
        tham_so = (
            dang_ban, danh_muc, danh_muc, gia_tu, gia_tu, gia_den, gia_den,
            loai_tru, loai_tru, loc, loc, tac_gia, tac_gia, giam_gia, con_hang, co_review, q, q, q, q,
        )
        cte, cot, nguon = "", self._cot_sach, self._nguon_sach
        if ky_doanh_so is not None:
            cte = self._CTE_DOANH_SO + " "
            cot += ", COALESCE(ds.so_ban, 0) AS so_ban_that "
            nguon += "LEFT JOIN doanh_so ds ON ds.ma_sach = s.ma "
            if sap_xep == "ban_chay":
                where.append("s.ton_kho > 0 AND ds.so_ban > 0")
            tham_so = (*ky_doanh_so, *tham_so)
        nguon += "WHERE " + " AND ".join(where)
        tong = 0 if chi_goi_y else self.conn.execute(
            cte + "SELECT COUNT(*) " + nguon, tham_so,
        ).fetchone()[0]
        so_trang = max(1, (tong + moi_trang - 1) // moi_trang)
        trang = min(max(1, trang), so_trang)
        sep, tham_so_xep = self._thu_tu_tim(sap_xep, q, ky_doanh_so)
        tham_so += tham_so_xep
        rows = self.conn.execute(
            cte + cot + nguon + f" ORDER BY {sep} LIMIT ? OFFSET ?",
            (*tham_so, moi_trang, (trang - 1) * moi_trang),
        )
        muc = [self._sach(row) for row in rows]
        return Trang(muc, trang, so_trang, len(muc) if chi_goi_y else tong)

    _nguon_sach = "FROM sach s JOIN danh_muc d ON d.ma = s.ma_danh_muc "
    def _thu_tu_tim(self, sap_xep, q, ky_doanh_so):
        sep = {
            "ban_chay": ("so_ban_that DESC, s.ngay_them DESC, s.ma DESC"
                         if ky_doanh_so is not None else "da_ban DESC, s.ma DESC"),
            "gia_tang": "s.gia, s.ma",
            "gia_giam": "s.gia DESC, s.ma",
            "ten": "khoa_tim(s.tieu_de), s.ma",
            "danh_gia": "diem_tb DESC, so_danh_gia DESC, s.ma DESC",
            "giam_sau": self._TY_LE_GIAM + " DESC, s.ma DESC",
            "moi": "s.ngay_them DESC, s.ma DESC",
        }.get(sap_xep, "s.ngay_them DESC, s.ma DESC")
        if q and sap_xep in (None, "", "lien_quan"):
            sep = """CASE WHEN khoa_tim(s.tieu_de) = ? THEN 0
                          WHEN instr(khoa_tim(s.tieu_de), ?) = 1 THEN 1
                          WHEN instr(khoa_tim(s.tieu_de), ?) > 0 THEN 2
                          WHEN instr(khoa_tim(s.tac_gia), ?) > 0 THEN 3
                          ELSE 4 END, """ + sep
            return sep, (q, q, q, q)
        return sep, ()

    _CTE_DOANH_SO = """WITH doanh_so AS (
        SELECT m.ma_sach, SUM(m.so_luong) AS so_ban
        FROM don_hang h JOIN muc_don m ON m.ma_don = h.ma
        WHERE h.trang_thai = 'hoan_thanh' AND NOT h.da_hoan_tien
          AND h.ghi_chu <> 'Đơn mẫu' AND h.cap_nhat_luc BETWEEN ? AND ?
          AND NOT EXISTS (SELECT 1 FROM thao_tac_dat_hang t
                          WHERE t.ma_don = h.ma AND t.ma LIKE 'du-lieu-mau-%')
        GROUP BY m.ma_sach
    )"""
    _CO_REVIEW = "EXISTS (SELECT 1 FROM bai_review r WHERE r.ma_sach = s.ma AND r.trang_thai = 'da_duyet')"
    _TY_LE_GIAM = "CASE WHEN s.gia_bia > s.gia THEN 1.0 - 1.0 * s.gia / s.gia_bia ELSE 0 END"
    _cot_sach = """SELECT s.*, d.duong_dan AS duong_dan_danh_muc,
        COALESCE((SELECT SUM(m.so_luong) FROM muc_don m JOIN don_hang h ON h.ma = m.ma_don
                  WHERE m.ma_sach = s.ma AND h.trang_thai = 'hoan_thanh'), 0) AS da_ban,
        COALESCE((SELECT AVG(g.so_sao) FROM danh_gia_con_hieu_luc g
                  WHERE g.ma_sach = s.ma), 0) AS diem_tb,
        (SELECT COUNT(*) FROM danh_gia_con_hieu_luc g WHERE g.ma_sach = s.ma) AS so_danh_gia,
        """ + _CO_REVIEW + " AS co_review "

    def luu(self, du_lieu, ma=None):
        if ma is None:
            return self.conn.execute(
                """INSERT INTO sach (tieu_de, tac_gia, nha_xuat_ban, nam_xuat_ban, so_trang,
                   gia, gia_bia, ton_kho, mo_ta, ma_danh_muc, anh_bia, mau_bia, dang_ban, ngay_them)
                   VALUES (:tieu_de, :tac_gia, :nha_xuat_ban, :nam_xuat_ban, :so_trang, :gia,
                   :gia_bia, :ton_kho, :mo_ta, :ma_danh_muc, :anh_bia, :mau_bia, :dang_ban, :ngay_them)""",
                du_lieu,
            ).lastrowid
        self.conn.execute(
            """UPDATE sach SET tieu_de=:tieu_de, tac_gia=:tac_gia, nha_xuat_ban=:nha_xuat_ban,
               nam_xuat_ban=:nam_xuat_ban, so_trang=:so_trang, gia=:gia, gia_bia=:gia_bia, mo_ta=:mo_ta,
               ma_danh_muc=:ma_danh_muc, anh_bia=:anh_bia, mau_bia=:mau_bia, dang_ban=:dang_ban
               WHERE ma=:ma""",
            dict(du_lieu, ma=ma),
        )
        return ma

    def ma_theo_tieu_de(self, tieu_de):
        rows = self.conn.execute("SELECT ma FROM sach WHERE tieu_de = ? ORDER BY ma LIMIT 2", (tieu_de,))
        return [row["ma"] for row in rows]

    def doi_trang_thai_ban(self, ma, dang_ban):
        return self.conn.execute(
            "UPDATE sach SET dang_ban = ? WHERE ma = ?", (dang_ban, ma),
        ).rowcount == 1

    def sap_het(self):
        rows = self.conn.execute(
            self._cot_sach + self._nguon_sach + """WHERE s.dang_ban = 1 AND s.ton_kho <= 5
                ORDER BY s.ton_kho, s.ma"""
        )
        return [self._sach(row) for row in rows]

    def noi_bat(self):
        row = self.conn.execute(
            self._cot_sach + self._nguon_sach + """WHERE s.dang_ban = 1 AND s.ton_kho > 0
                ORDER BY (s.gia < s.gia_bia) DESC, da_ban DESC, s.ma DESC LIMIT 1"""
        ).fetchone()
        return self._sach(row)

    def lay(self, ma, ky_doanh_so=None):
        if ky_doanh_so is None:
            sql = self._cot_sach + self._nguon_sach + "WHERE s.ma = ?"
            tham_so = (ma,)
        else:
            sql = (self._CTE_DOANH_SO + " " + self._cot_sach + ", COALESCE(ds.so_ban, 0) AS so_ban_that "
                   + self._nguon_sach + "LEFT JOIN doanh_so ds ON ds.ma_sach = s.ma WHERE s.ma = ?")
            tham_so = (*ky_doanh_so, ma)
        return self._sach(self.conn.execute(sql, tham_so).fetchone())

    @staticmethod
    def _sach(row):
        if row is None:
            return None
        du_lieu = dict(row)
        du_lieu["ngay_them"] = datetime.fromisoformat(du_lieu["ngay_them"])
        du_lieu["dang_ban"] = bool(du_lieu["dang_ban"])
        du_lieu["co_review"] = bool(du_lieu.get("co_review"))
        return Sach(**du_lieu)

class KhoKhamPha(KhoSach):
    def theo_ma(self, cac_ma, *, dang_ban=True):
        dieu_kien = "s.dang_ban = 1 AND " if dang_ban else ""
        rows = _theo_cac_ma(
            self.conn, cac_ma, self._cot_sach + self._nguon_sach + "WHERE " + dieu_kien + "s.ma",
        )
        sach = {row["ma"]: self._sach(row) for row in rows}
        return [sach[ma] for ma in cac_ma if ma in sach]

    def cung_tac_gia_va_the_loai(self, sach):
        rows = self.conn.execute(
            """WITH ung_vien AS (""" + self._cot_sach
            + """, (khoa_tim(trim(s.tac_gia)) = khoa_tim(trim(?)) AND trim(?) <> '') AS cung_tac_gia """
            + self._nguon_sach + """WHERE s.dang_ban = 1 AND s.ma <> ?
                AND (s.ma_danh_muc = ? OR khoa_tim(trim(s.tac_gia)) = khoa_tim(trim(?)))),
            thu_tu AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY cung_tac_gia ORDER BY (ton_kho > 0) DESC, ngay_them DESC, ma DESC
                ) AS vi_tri
                FROM ung_vien
            )
            SELECT * FROM thu_tu
            WHERE (cung_tac_gia AND (vi_tri <= 6 OR ma_danh_muc = ?))
               OR (NOT cung_tac_gia AND ma_danh_muc = ? AND vi_tri <= 4)
            ORDER BY cung_tac_gia DESC, vi_tri""",
            (sach.tac_gia, sach.tac_gia, sach.ma, sach.ma_danh_muc, sach.tac_gia,
             sach.ma_danh_muc, sach.ma_danh_muc),
        )
        tac_gia, the_loai = [], []
        for row in rows:
            data = dict(row)
            cung = data.pop("cung_tac_gia")
            data.pop("vi_tri")
            muc = self._sach(data)
            if cung and len(tac_gia) < 6:
                tac_gia.append(muc)
            elif muc.ma_danh_muc == sach.ma_danh_muc:
                the_loai.append(muc)
        the_loai.sort(key=lambda muc: (muc.ton_kho > 0, muc.ngay_them, muc.ma), reverse=True)
        return tac_gia, the_loai[:4]

    def ung_vien_trang_chu(self, tu_luc, den_luc):
        rows = self.conn.execute(
            self._CTE_DOANH_SO + ", ung_vien AS (" + self._cot_sach + """,
                COALESCE(ds.so_ban, 0) AS so_ban_that, r.noi_dung AS noi_dung_review,
                r.duyet_luc AS luc_duyet, """ + self._TY_LE_GIAM + " AS ty_le_giam, "
            + """ROW_NUMBER() OVER (
                    PARTITION BY s.ngay_them, s.ma_danh_muc ORDER BY s.ma DESC
                ) AS luot_the_loai """
            + self._nguon_sach + """
                LEFT JOIN doanh_so ds ON ds.ma_sach = s.ma
                LEFT JOIN bai_review r ON r.ma_sach = s.ma AND r.trang_thai = 'da_duyet'
                WHERE s.dang_ban = 1 AND s.ton_kho > 0
            ), hang AS (
                SELECT *,
                    ROW_NUMBER() OVER (ORDER BY ngay_them DESC, luot_the_loai, ma DESC) AS hang_moi,
                    ROW_NUMBER() OVER (ORDER BY so_ban_that DESC, ngay_them DESC, ma DESC) AS hang_ban,
                    ROW_NUMBER() OVER (ORDER BY ty_le_giam DESC, ma DESC) AS hang_giam,
                    ROW_NUMBER() OVER (ORDER BY luc_duyet DESC, ma DESC) AS hang_review,
                    ROW_NUMBER() OVER (
                        ORDER BY (duong_dan_danh_muc <> 'trinh-tham-kinh-di') DESC,
                                 co_review DESC, (anh_bia IS NOT NULL) DESC, so_ban_that DESC, ngay_them DESC, ma DESC
                    ) AS hang_noi_bat
                FROM ung_vien
            ) SELECT * FROM hang
              WHERE min(hang_moi, hang_ban, hang_giam, hang_review, hang_noi_bat) <= 44""",
            (tu_luc, den_luc),
        )
        ket_qua = []
        for row in rows:
            data = dict(row)
            hang = {ten: data.pop(ten) for ten in (
                "hang_moi", "hang_ban", "hang_giam", "hang_review", "hang_noi_bat",
                "so_ban_that", "noi_dung_review", "ty_le_giam",
            )}
            data.pop("luc_duyet")
            data.pop("luot_the_loai")
            data["so_ban_that"] = hang["so_ban_that"]
            ket_qua.append(dict(hang, sach=self._sach(data)))
        return ket_qua


class KhoDanhMuc:
    def __init__(self, conn):
        self.conn = conn

    def them(self, ten, duong_dan, thu_tu):
        return self.conn.execute(
            "INSERT OR IGNORE INTO danh_muc (ten, duong_dan, thu_tu) VALUES (?, ?, ?)",
            (ten, duong_dan, thu_tu),
        ).rowcount == 1

    def sua(self, ma, ten, duong_dan, thu_tu):
        return self.conn.execute(
            "UPDATE OR IGNORE danh_muc SET ten = ?, duong_dan = ?, thu_tu = ? WHERE ma = ?",
            (ten, duong_dan, thu_tu, ma),
        ).rowcount == 1

    def xoa(self, ma):
        return self.conn.execute(
            """DELETE FROM danh_muc WHERE ma = ?
               AND NOT EXISTS (SELECT 1 FROM sach WHERE ma_danh_muc = ?)""",
            (ma, ma),
        ).rowcount == 1

    def danh_sach(self) -> list[DanhMuc]:
        rows = self.conn.execute("SELECT * FROM danh_muc ORDER BY thu_tu, ten")
        return [DanhMuc(**dict(row)) for row in rows]

    def danh_sach_kem_dem_sach(self) -> list[DanhMucDemSach]:
        rows = self.conn.execute(
            """SELECT d.*, COUNT(s.ma) AS so_sach,
                      SUM(CASE WHEN s.dang_ban = 1 THEN 1 ELSE 0 END) AS so_sach_dang_ban
               FROM danh_muc d LEFT JOIN sach s ON s.ma_danh_muc = d.ma
               GROUP BY d.ma ORDER BY d.thu_tu, d.ten"""
        )
        ket_qua = []
        for row in rows:
            du_lieu = dict(row)
            so_sach = du_lieu.pop("so_sach")
            so_sach_dang_ban = du_lieu.pop("so_sach_dang_ban")
            ket_qua.append(DanhMucDemSach(DanhMuc(**du_lieu), so_sach, so_sach_dang_ban))
        return ket_qua


class KhoKhachHang:
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _khach(row):
        if row is None:
            return None
        du_lieu = dict(row)
        du_lieu["ngay_tao"] = datetime.fromisoformat(du_lieu["ngay_tao"])
        return KhachHang(**du_lieu)

    def lay(self, ma):
        return self._khach(self.conn.execute("SELECT * FROM khach_hang WHERE ma = ?", (ma,)).fetchone())

    def danh_sach(self):
        rows = self.conn.execute(
            """SELECT k.*, COUNT(d.ma) AS so_don,
                      COALESCE(SUM(CASE WHEN d.trang_thai = ? THEN d.tong ELSE 0 END), 0) AS tong_chi
               FROM khach_hang k LEFT JOIN don_hang d ON d.ma_khach = k.ma
               GROUP BY k.ma ORDER BY k.ngay_tao DESC, k.ma DESC""",
            (TrangThaiDon.HOAN_THANH,),
        )
        ket_qua = []
        for row in rows:
            khach = dict(row)
            so_don, tong_chi = khach.pop("so_don"), khach.pop("tong_chi")
            ket_qua.append(KhachTongHop(self._khach(khach), so_don, tong_chi))
        return ket_qua

    def dem(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM khach_hang").fetchone()[0]

    def cap_nhat_dia_chi(self, ma, dia_chi):
        self.conn.execute("UPDATE khach_hang SET dia_chi = ? WHERE ma = ?", (dia_chi, ma))

    def cap_nhat_ho_so(self, ma, ho_ten, dien_thoai, dia_chi):
        self.conn.execute(
            "UPDATE khach_hang SET ho_ten = ?, dien_thoai = ?, dia_chi = ? WHERE ma = ?",
            (ho_ten, dien_thoai, dia_chi, ma),
        )

    def theo_email(self, email):
        return self._khach(self.conn.execute(
            "SELECT * FROM khach_hang WHERE email = ?", (email,),
        ).fetchone())

    def them(self, ho_ten, email, dien_thoai, mat_khau_bam, luc, *, dia_chi=""):
        ma = self.conn.execute(
            """INSERT INTO khach_hang (ho_ten, email, dien_thoai, dia_chi, mat_khau_bam, ngay_tao)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ho_ten, email, dien_thoai, dia_chi, mat_khau_bam, luc.isoformat()),
        ).lastrowid
        return self.lay(ma)


def _theo_cac_ma(conn, cac_ma, sql):
    # Giới hạn mỗi nhóm để các file SQLite dùng cấu hình cũ vẫn nhận đủ tham số.
    cac_ma = list(dict.fromkeys(cac_ma))
    for dau in range(0, len(cac_ma), 900):
        nhom = cac_ma[dau:dau+900]
        placeholders = ", ".join("?" for _ in nhom)
        yield from conn.execute(f"{sql} IN ({placeholders})", nhom)


class KhoDanhGia:
    def __init__(self, conn):
        self.conn = conn

    def doi_an(self, ma):
        return self.conn.execute(
            "UPDATE danh_gia SET an = 1 - an WHERE ma = ?", (ma,),
        ).rowcount == 1

    def danh_sach(self) -> list[DanhGiaQuanLy]:
        sach = [truong.name for truong in fields(Sach) if truong.name != "so_ban_that"]
        khach = [truong.name for truong in fields(KhachHang)]
        cot = ", ".join(
            f"{bang}.{ten} AS {bang}_{ten}" for bang, ds in (("s", sach), ("k", khach)) for ten in ds
        )
        sql_sach = KhoSach._cot_sach + KhoSach._nguon_sach
        rows = self.conn.execute(
            f"""SELECT g.*, {cot} FROM danh_gia g
                JOIN ({sql_sach}) s ON s.ma = g.ma_sach
                JOIN khach_hang k ON k.ma = g.ma_khach
                ORDER BY g.tao_luc DESC, g.ma DESC"""
        )
        return [
            DanhGiaQuanLy(
                self._danh_gia({truong.name: row[truong.name] for truong in fields(DanhGia)}),
                KhoSach._sach({ten: row[f"s_{ten}"] for ten in sach}),
                KhoKhachHang._khach({ten: row[f"k_{ten}"] for ten in khach}),
            )
            for row in rows
        ]

    @staticmethod
    def _danh_gia(du_lieu):
        du_lieu["tao_luc"] = datetime.fromisoformat(du_lieu["tao_luc"])
        du_lieu["an"] = bool(du_lieu["an"])
        return DanhGia(**du_lieu)

    def cua_sach(self, ma):
        rows = self.conn.execute(
            """SELECT d.*, k.ho_ten AS ten_khach FROM danh_gia_con_hieu_luc d
               JOIN khach_hang k ON k.ma = d.ma_khach
               WHERE d.ma_sach = ? ORDER BY d.tao_luc DESC, d.ma DESC""",
            (ma,),
        )
        ket_qua = []
        for row in rows:
            du_lieu = dict(row)
            ten_khach = du_lieu.pop("ten_khach")
            ket_qua.append(DanhGiaCongKhai(self._danh_gia(du_lieu), ten_khach))
        return ket_qua

    def cua_khach(self, ma_sach, ma_khach):
        row = self.conn.execute(
            "SELECT * FROM danh_gia WHERE ma_sach = ? AND ma_khach = ?",
            (ma_sach, ma_khach),
        ).fetchone()
        return self._danh_gia(dict(row)) if row is not None else None

    def da_mua(self, ma_sach, ma_khach):
        return self.conn.execute(
            """SELECT 1 FROM muc_don m JOIN don_hang h ON h.ma = m.ma_don
               WHERE m.ma_sach = ? AND h.ma_khach = ? AND h.trang_thai <> ? LIMIT 1""",
            (ma_sach, ma_khach, TrangThaiDon.DA_HUY),
        ).fetchone() is not None

    def luu(self, ma_sach, ma_khach, so_sao, noi_dung, luc):
        self.conn.execute(
            """INSERT INTO danh_gia (ma_sach, ma_khach, so_sao, noi_dung, tao_luc)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(ma_sach, ma_khach) DO UPDATE
               SET so_sao = excluded.so_sao, noi_dung = excluded.noi_dung,
                   tao_luc = excluded.tao_luc""",
            (ma_sach, ma_khach, so_sao, noi_dung, luc.isoformat()),
        )


class KhoMaGiamGia:
    def __init__(self, conn):
        self.conn = conn

    def lay(self, ma):
        return self._ma(self.conn.execute("SELECT * FROM ma_giam_gia WHERE ma = ?", (ma,)).fetchone())

    @staticmethod
    def _ma(row):
        if row is None:
            return None
        du_lieu = dict(row)
        du_lieu["het_han"] = date.fromisoformat(du_lieu["het_han"]) if du_lieu["het_han"] else None
        du_lieu["dang_bat"] = bool(du_lieu["dang_bat"])
        return MaGiamGia(**du_lieu)

    def them(self, du_lieu):
        return self.conn.execute(
            """INSERT OR IGNORE INTO ma_giam_gia
               (ma, kieu, gia_tri, don_toi_thieu, het_han, so_luot_toi_da)
               VALUES (:ma, :kieu, :gia_tri, :don_toi_thieu, :het_han, :so_luot_toi_da)""",
            du_lieu,
        ).rowcount == 1

    def bat_tat(self, ma):
        return self.conn.execute(
            "UPDATE ma_giam_gia SET dang_bat = 1 - dang_bat WHERE ma = ?", (ma,),
        ).rowcount == 1

    def danh_sach(self):
        return [self._ma(row) for row in self.conn.execute("SELECT * FROM ma_giam_gia ORDER BY ma")]

    def doi_luot(self, ma, chenh_lech):
        return self.conn.execute(
            """UPDATE ma_giam_gia SET da_dung = da_dung + ?
               WHERE ma = ? AND da_dung + ? >= 0
               AND (so_luot_toi_da IS NULL OR da_dung + ? <= so_luot_toi_da)""",
            (chenh_lech, ma, chenh_lech, chenh_lech),
        ).rowcount == 1


class KhoBaoCaoDon:
    def __init__(self, conn):
        self.conn = conn

    def xuat_don(self) -> list[DongXuatDon]:
        rows = self.conn.execute(
            """SELECT ma_tra_cuu, ho_ten, dien_thoai, dia_chi, trang_thai, phuong_thuc,
                      tam_tinh, giam_gia, phi_giao, tong, tao_luc
               FROM don_hang ORDER BY tao_luc DESC, ma DESC"""
        )
        ket_qua = []
        for row in rows:
            don = dict(row)
            don["trang_thai"] = TrangThaiDon(don["trang_thai"])
            don["phuong_thuc"] = PhuongThuc(don["phuong_thuc"])
            don["tao_luc"] = datetime.fromisoformat(don["tao_luc"])
            ket_qua.append(DongXuatDon(**don))
        return ket_qua

    def dem_cho_xac_nhan(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM don_hang WHERE trang_thai = ?", (TrangThaiDon.CHO_XAC_NHAN,),
        ).fetchone()[0]

    def doanh_thu(self, tu_ngay=None) -> list[DoanhThuNgay]:
        loc = " AND tao_luc >= ?" if tu_ngay is not None else ""
        tham_so = (TrangThaiDon.HOAN_THANH, tu_ngay.isoformat()) if loc else (TrangThaiDon.HOAN_THANH,)
        rows = self.conn.execute(
            """SELECT substr(tao_luc, 1, 10) AS ngay, SUM(tam_tinh - giam_gia) AS tien
               FROM don_hang WHERE trang_thai = ?""" + loc + " GROUP BY ngay ORDER BY ngay",
            tham_so,
        )
        return [DoanhThuNgay(date.fromisoformat(row["ngay"]), row["tien"]) for row in rows]


class KhoDonHang:
    def __init__(self, conn):
        self.conn = conn

    def _don(self, row):
        return self._nhieu_don([row])[0] if row is not None else None

    def _nhieu_don(self, rows):
        rows = list(rows)
        cac_muc = {row["ma"]: [] for row in rows}
        sql = """SELECT m.ma_don, m.ma_sach, m.tieu_de, m.don_gia, m.so_luong,
                        s.mau_bia, d.duong_dan AS duong_dan_danh_muc, s.anh_bia, s.tac_gia
                 FROM muc_don m
                 LEFT JOIN sach s ON s.ma = m.ma_sach
                 LEFT JOIN danh_muc d ON d.ma = s.ma_danh_muc
                 WHERE m.ma_don"""
        for row in _theo_cac_ma(self.conn, cac_muc, sql):
            item = dict(row)
            cac_muc[item.pop("ma_don")].append(MucDon(**item))
        return [self._doc_don(row, sorted(cac_muc[row["ma"]], key=lambda item: item.ma_sach)) for row in rows]

    @staticmethod
    def _doc_don(row, muc):
        du_lieu = dict(row)
        du_lieu["trang_thai"] = TrangThaiDon(du_lieu["trang_thai"])
        du_lieu["phuong_thuc"] = PhuongThuc(du_lieu["phuong_thuc"])
        for truong in ("tao_luc", "cap_nhat_luc"):
            du_lieu[truong] = datetime.fromisoformat(du_lieu[truong])
        for truong in ("da_thanh_toan", "da_hoan_tien"):
            du_lieu[truong] = bool(du_lieu[truong])
        return DonHang(**du_lieu, muc=muc)

    def lay(self, ma):
        return self._don(self.conn.execute("SELECT * FROM don_hang WHERE ma = ?", (ma,)).fetchone())

    def danh_sach(self, trang_thai=None, trang=1, moi_trang=15, *, q="", dien_thoai=""):
        cac_dieu_kien, tham_so = [], []
        if trang_thai is not None:
            cac_dieu_kien.append("trang_thai = ?")
            tham_so.append(trang_thai)
        if q:
            cac_dieu_kien.append(
                "(instr(lower(ma_tra_cuu), ?) > 0 OR instr(khoa_tim(ho_ten), ?) > 0 "
                "OR instr(dien_thoai, ?) > 0)"
            )
            tham_so.extend((q.casefold(), khoa_tim(q), dien_thoai or q))
        dieu_kien = " WHERE " + " AND ".join(cac_dieu_kien) if cac_dieu_kien else ""
        tong = self.conn.execute("SELECT COUNT(*) FROM don_hang" + dieu_kien, tham_so).fetchone()[0]
        so_trang = max(1, (tong + moi_trang - 1) // moi_trang)
        trang = min(max(1, trang), so_trang)
        rows = self.conn.execute(
            "SELECT * FROM don_hang" + dieu_kien + " ORDER BY tao_luc DESC, ma DESC LIMIT ? OFFSET ?",
            (*tham_so, moi_trang, (trang - 1) * moi_trang),
        )
        return Trang(self._nhieu_don(rows), trang, so_trang, tong)

    def cua_khach(self, ma):
        rows = self.conn.execute(
            "SELECT * FROM don_hang WHERE ma_khach = ? ORDER BY tao_luc DESC, ma DESC",
            (ma,),
        )
        return self._nhieu_don(rows)

    def lay_theo_ma_tra_cuu(self, ma):
        return self._don(self.conn.execute(
            "SELECT * FROM don_hang WHERE ma_tra_cuu = ?", (ma,),
        ).fetchone())

    def lay_theo_thao_tac(self, ma_thao_tac):
        return self._don(self.conn.execute(
            """SELECT don_hang.* FROM don_hang JOIN thao_tac_dat_hang
               ON don_hang.ma = thao_tac_dat_hang.ma_don WHERE thao_tac_dat_hang.ma = ?""",
            (ma_thao_tac,),
        ).fetchone())

    def tao_ma_tra_cuu(self):
        for _ in range(10):
            ma = "".join(choice(ascii_uppercase + digits) for _ in range(8))
            if self.lay_theo_ma_tra_cuu(ma) is None:
                return ma
        raise RuntimeError("Không tạo được mã tra cứu duy nhất.")

    def them(self, du_lieu, muc, ma_thao_tac):
        ma_don = self.conn.execute(
            """INSERT INTO don_hang
               (ma_tra_cuu, ma_khach, ho_ten, dien_thoai, dia_chi, ghi_chu, phuong_thuc,
                trang_thai, tam_tinh, giam_gia, phi_giao, tong, ma_giam_gia, tao_luc, cap_nhat_luc)
               VALUES (:ma_tra_cuu, :ma_khach, :ho_ten, :dien_thoai, :dia_chi, :ghi_chu,
                       :phuong_thuc, :trang_thai, :tam_tinh, :giam_gia, :phi_giao, :tong,
                       :ma_giam_gia, :tao_luc, :cap_nhat_luc)""",
            du_lieu,
        ).lastrowid
        self.conn.executemany(
            "INSERT INTO muc_don (ma_don, ma_sach, tieu_de, don_gia, so_luong) VALUES (?, ?, ?, ?, ?)",
            [(ma_don, m.ma_sach, m.tieu_de, m.don_gia, m.so_luong) for m in muc],
        )
        self.conn.execute(
            "INSERT INTO thao_tac_dat_hang (ma, ma_don) VALUES (?, ?)", (ma_thao_tac, ma_don),
        )
        return self.lay(ma_don)

    def doi_trang_thai(self, ma, trang_thai, da_hoan_tien, da_thanh_toan, luc):
        self.conn.execute(
            """UPDATE don_hang SET trang_thai = ?, da_hoan_tien = ?, da_thanh_toan = ?,
               cap_nhat_luc = ? WHERE ma = ?""",
            (trang_thai, da_hoan_tien, da_thanh_toan, luc.isoformat(), ma),
        )
        return self.lay(ma)

    def xac_nhan_thanh_toan(self, ma, luc):
        self.conn.execute(
            "UPDATE don_hang SET da_thanh_toan = 1, cap_nhat_luc = ? WHERE ma = ?",
            (luc.isoformat(), ma),
        )
        return self.lay(ma)

class KhoDuLieuMau:
    def __init__(self, conn):
        self.conn = conn

    def ghi_nhan(self, ma="sach_mau") -> bool:
        return self.conn.execute(
            "INSERT OR IGNORE INTO du_lieu_da_nap (ma) VALUES (?)", (ma,),
        ).rowcount == 1


class KhoReview:
    _SQL_KEM_SACH = """SELECT r.*, s.tieu_de AS sach_tieu_de,
                               s.tac_gia AS sach_tac_gia, s.anh_bia AS sach_anh_bia
                        FROM bai_review r JOIN sach s ON s.ma = r.ma_sach"""

    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _bai(row):
        if row is None:
            return None
        du_lieu = dict(row)
        du_lieu["trang_thai"] = TrangThaiReview(du_lieu["trang_thai"])
        du_lieu["tao_luc"] = datetime.fromisoformat(du_lieu["tao_luc"])
        if du_lieu["duyet_luc"]:
            du_lieu["duyet_luc"] = datetime.fromisoformat(du_lieu["duyet_luc"])
        if "sach_tieu_de" in du_lieu:
            du_lieu["sach"] = SachCuaReview(
                du_lieu.pop("sach_tieu_de"),
                du_lieu.pop("sach_tac_gia"),
                du_lieu.pop("sach_anh_bia"),
            )
        return BaiReview(**du_lieu)

    def lay(self, ma):
        return self._bai(self.conn.execute(
            self._SQL_KEM_SACH + " WHERE r.ma = ?", (ma,),
        ).fetchone())

    def da_duyet_cua_sach(self, ma_sach):
        return self._bai(self.conn.execute(
            "SELECT * FROM bai_review WHERE ma_sach = ? AND trang_thai = ?",
            (ma_sach, TrangThaiReview.DA_DUYET),
        ).fetchone())

    def sach_chua_co_review(self):
        rows = self.conn.execute(
            """SELECT s.ma, s.tieu_de, s.tac_gia FROM sach s
               WHERE NOT EXISTS (SELECT 1 FROM bai_review r WHERE r.ma_sach = s.ma)
               ORDER BY khoa_tim(s.tieu_de), s.ma"""
        )
        return [dict(row) for row in rows]

    def danh_sach(self, trang_thai=None):
        rows = self.conn.execute(
            self._SQL_KEM_SACH + """ WHERE (? IS NULL OR r.trang_thai = ?)
               ORDER BY r.tao_luc DESC, r.ma DESC""",
            (trang_thai, trang_thai),
        )
        return [self._bai(row) for row in rows]

    def tao_nhap(self, ma_sach, tieu_de, noi_dung, tac_gia, luc):
        cur = self.conn.execute(
            """INSERT INTO bai_review (ma_sach, tieu_de, noi_dung, tac_gia_review, trang_thai, tao_luc)
               VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(ma_sach) DO NOTHING""",
            (ma_sach, tieu_de, noi_dung, tac_gia, TrangThaiReview.NHAP, luc.isoformat()),
        )
        return self.lay(cur.lastrowid) if cur.rowcount else None

    def sua(self, ma, tieu_de, noi_dung, tac_gia):
        self.conn.execute(
            """UPDATE bai_review SET tieu_de = ?, noi_dung = ?, tac_gia_review = ?,
               trang_thai = ?, duyet_luc = NULL WHERE ma = ?""",
            (tieu_de, noi_dung, tac_gia, TrangThaiReview.NHAP, ma),
        )
        return self.lay(ma)

    def doi_trang_thai(self, ma, trang_thai, luc):
        self.conn.execute(
            "UPDATE bai_review SET trang_thai = ?, duyet_luc = ? WHERE ma = ?",
            (trang_thai, luc.isoformat() if luc else None, ma),
        )
        return self.lay(ma)
