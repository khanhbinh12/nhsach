"""Dựng bản xem trước tĩnh cho mọi template bằng Jinja2 StrictUndefined và dữ liệu từ sach_mau.json.

Chạy:
    python xem_truoc.py

Tệp xuất ra nằm trong `xem_truoc/*.html` dùng đường dẫn CSS tương đối
để mở trực tiếp bằng trình duyệt và dùng cho `kiem_giao_dien/tran_ngang.py`.
Thoát mã khác 0 nếu có bất kỳ template nào chưa được dựng hoặc gặp lỗi Jinja.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from nha_sach.mo_hinh import BaiReview, BiaSach, ChinhSachGiaoHang, TrangThaiReview


GOC = Path(__file__).resolve().parent
THU_MUC_TEMPLATE = GOC / "templates"
THU_MUC_RA = GOC / "xem_truoc"

DUONG_DAN_DU_LIEU = [
    GOC / "du_lieu" / "sach_mau.json",
]


class TrangThaiDon(Enum):
    CHO_XAC_NHAN = "cho_xac_nhan"
    DANG_CHUAN_BI = "dang_chuan_bi"
    DANG_GIAO = "dang_giao"
    HOAN_THANH = "hoan_thanh"
    DA_HUY = "da_huy"

    @property
    def nhan(self) -> str:
        return {
            "cho_xac_nhan": "Chờ xác nhận",
            "dang_chuan_bi": "Đang chuẩn bị",
            "dang_giao": "Đang giao hàng",
            "hoan_thanh": "Hoàn thành",
            "da_huy": "Đã hủy",
        }[self.value]


class PhuongThucThanhToan(Enum):
    COD = "cod"
    CHUYEN_KHOAN = "chuyen_khoan"

    @property
    def nhan(self) -> str:
        return {
            "cod": "Trả tiền khi nhận hàng",
            "chuyen_khoan": "Chuyển khoản",
        }[self.value]


@dataclass
class DanhMuc:
    ma: int
    ten: str
    duong_dan: str
    thu_tu: int


@dataclass
class Sach:
    ma: int
    tieu_de: str
    tac_gia: str
    nha_xuat_ban: str | None
    nam_xuat_ban: int | None
    so_trang: int | None
    gia: int
    gia_bia: int
    ton_kho: int
    mo_ta: str
    ma_danh_muc: int
    anh_bia: str | None
    mau_bia: str
    dang_ban: bool
    ngay_them: datetime
    da_ban: int
    diem_tb: float
    so_danh_gia: int
    duong_dan_danh_muc: str | None = None
    co_review: bool = False
    so_ban_that: int = 0

    @property
    def bia(self) -> BiaSach:
        return BiaSach.tao(self.tieu_de, self.mau_bia, self.duong_dan_danh_muc)


@dataclass
class KhachHang:
    ma: int
    ho_ten: str
    email: str
    dien_thoai: str
    dia_chi: str
    mat_khau_bam: str
    ngay_tao: datetime


@dataclass
class MucDon:
    ma_sach: int
    tieu_de: str
    don_gia: int
    so_luong: int
    mau_bia: str | None = None
    duong_dan_danh_muc: str | None = None
    anh_bia: str | None = None
    tac_gia: str | None = None

    @property
    def bia(self) -> BiaSach:
        if self.mau_bia:
            return BiaSach.tao(self.tieu_de, self.mau_bia, self.duong_dan_danh_muc)
        bang_mau = (
            "#2e7d32", "#1565c0", "#00695c", "#9a3412",
            "#4527a0", "#37474f", "#6a1b9a", "#1e3a5f",
        )
        return BiaSach.tao(self.tieu_de, bang_mau[self.ma_sach % len(bang_mau)], None)


@dataclass
class BaiReviewXemTruoc(BaiReview):
    sach: Sach | None = None


@dataclass
class DonHang:
    ma: int
    ma_tra_cuu: str
    ma_khach: int | None
    ho_ten: str
    dien_thoai: str
    dia_chi: str
    ghi_chu: str
    phuong_thuc: PhuongThucThanhToan
    da_thanh_toan: bool
    trang_thai: TrangThaiDon
    tam_tinh: int
    giam_gia: int
    phi_giao: int
    tong: int
    ma_giam_gia: str | None
    tao_luc: datetime
    cap_nhat_luc: datetime
    muc: list[MucDon]
    da_hoan_tien: bool = False


@dataclass
class MaGiamGia:
    ma: str
    kieu: str
    gia_tri: int
    don_toi_thieu: int
    het_han: str | None
    so_luot_toi_da: int | None
    da_dung: int
    dang_bat: bool


@dataclass
class DanhGia:
    ma: int
    ma_sach: int
    ma_khach: int
    so_sao: int
    noi_dung: str
    tao_luc: datetime
    an: bool


@dataclass
class Trang:
    muc: list
    trang: int
    so_trang: int
    tong: int


@dataclass
class XemGio:
    muc: list[dict]
    tam_tinh: int
    ma_giam_gia: MaGiamGia | None
    giam_gia: int
    phi_giao: int
    tong: int
    canh_bao: list[str]

    @property
    def con_thieu_mien_phi(self) -> int:
        return ChinhSachGiaoHang().con_thieu(self.tam_tinh - self.giam_gia)


class GiaRequest:
    def __init__(self, path: str = "/", args: dict[str, str] | None = None) -> None:
        self.path = path
        self.args = args or {}
        self.full_path = path


QR_SVG_MAU = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 29 29" shape-rendering="crispEdges" role="img" aria-label="Mã QR thanh toán mẫu">'
    '<rect width="29" height="29" fill="#ffffff"/>'
    '<path fill="#181a20" d="'
    "M2,2h7v7h-7zM3,3v5h5v-5zM4,4h3v3h-3z"
    "M20,2h7v7h-7zM21,3v5h5v-5zM22,4h3v3h-3z"
    "M2,20h7v7h-7zM3,21v5h5v-5zM4,22h3v3h-3z"
    "M11,2h2v2h-2zM15,2h2v3h-2zM11,6h4v2h-4zM17,6h1v3h-1z"
    "M2,11h3v2h-3zM7,11h3v2h-3zM12,10h5v3h-5zM19,11h3v2h-3zM24,11h3v2h-3z"
    "M3,15h4v2h-4zM9,14h2v4h-2zM13,15h4v2h-4zM19,15h2v4h-2zM23,15h4v2h-4z"
    "M11,20h3v2h-3zM16,20h4v2h-4zM22,20h5v2h-5z"
    "M11,24h2v3h-2zM15,24h3v3h-3zM20,24h2v3h-2zM24,24h3v3h-3z"
    '"/></svg>'
)


def chuan_nfc(chuoi: str | None) -> str | None:
    if chuoi is None:
        return None
    return unicodedata.normalize("NFC", chuoi)


def bo_loc_tien(gia_tri: int | float | None) -> str:
    so = int(gia_tri or 0)
    return f"{so:,}".replace(",", ".") + " đ"


def bo_loc_ngay(gia_tri: datetime | None) -> str:
    if not gia_tri:
        return ""
    return gia_tri.strftime("%d/%m/%Y %H:%M")


def anh_bia_xem_truoc(anh_bia: str | None) -> str | None:
    """Đổi đường dẫn /bia-ebook/<ten> sang đường dẫn tương đối tới du_lieu/bia/ cho bản xem trước tĩnh."""
    if not anh_bia:
        return None
    if anh_bia.startswith("/bia-ebook/"):
        ten = anh_bia.removeprefix("/bia-ebook/")
        if (GOC / "du_lieu" / "bia" / ten).is_file():
            return f"../du_lieu/bia/{ten}"
    return anh_bia


def gia_url_for(endpoint: str, **tham_so: str) -> str:
    if endpoint == "static":
        return f"../static/{tham_so.get('filename', '')}"
    return "/"


def tim_tep_sach_mau() -> Path:
    for duong_dan in DUONG_DAN_DU_LIEU:
        if duong_dan.is_file():
            return duong_dan
    danh_sach = ", ".join(str(p) for p in DUONG_DAN_DU_LIEU)
    raise FileNotFoundError(f"Khong tim thay sach_mau.json tai: {danh_sach}")


def nap_kho_gia() -> dict:
    tep_du_lieu = tim_tep_sach_mau()
    goc_json = json.loads(tep_du_lieu.read_text(encoding="utf-8"))

    danh_muc_ds: list[DanhMuc] = []
    ma_theo_slug: dict[str, int] = {}
    dm_theo_ma: dict[int, DanhMuc] = {}
    for thu_tu, muc in enumerate(goc_json["danh_muc"], start=1):
        dm = DanhMuc(
            ma=thu_tu,
            ten=chuan_nfc(muc["ten"]) or "",
            duong_dan=muc["duong_dan"],
            thu_tu=thu_tu,
        )
        danh_muc_ds.append(dm)
        ma_theo_slug[dm.duong_dan] = dm.ma
        dm_theo_ma[dm.ma] = dm

    sao_theo_sach: dict[str, list[int]] = defaultdict(list)
    dg_goc_theo_sach: dict[str, list[dict]] = defaultdict(list)
    for dg in goc_json.get("danh_gia", []):
        ten_sach = chuan_nfc(dg["tieu_de_sach"]) or ""
        sao_theo_sach[ten_sach].append(int(dg["so_sao"]))
        dg_goc_theo_sach[ten_sach].append(dg)

    moc = datetime(2026, 11, 24, 18, 0)
    sach_ds: list[Sach] = []
    dem_theo_dm: Counter[int] = Counter()

    for idx, s in enumerate(goc_json["sach"], start=1):
        tieu_de = chuan_nfc(s["tieu_de"]) or ""
        ds_sao = sao_theo_sach.get(tieu_de, [])
        so_dg = len(ds_sao)
        diem_tb = round(sum(ds_sao) / so_dg, 1) if so_dg else 0.0
        ma_dm = ma_theo_slug[s["danh_muc"]]
        dem_theo_dm[ma_dm] += 1

        co_giam = int(s["gia_bia"]) > int(s["gia"])
        da_ban = 35 + (so_dg * 95) + (120 if co_giam else 0) + ((30 - idx) * 6)
        if int(s["ton_kho"]) == 0:
            da_ban = 148

        sach_ds.append(
            Sach(
                ma=idx,
                tieu_de=tieu_de,
                tac_gia=chuan_nfc(s["tac_gia"]) or "",
                nha_xuat_ban=chuan_nfc(s.get("nha_xuat_ban")),
                nam_xuat_ban=s.get("nam_xuat_ban"),
                so_trang=s.get("so_trang"),
                gia=int(s["gia"]),
                gia_bia=int(s["gia_bia"]),
                ton_kho=int(s["ton_kho"]),
                mo_ta=chuan_nfc(s.get("mo_ta")) or "",
                ma_danh_muc=ma_dm,
                anh_bia=anh_bia_xem_truoc(s.get("anh_bia")),
                mau_bia=s["mau_bia"],
                dang_ban=True,
                ngay_them=moc - timedelta(hours=idx * 5),
                da_ban=da_ban,
                diem_tb=diem_tb,
                so_danh_gia=so_dg,
                duong_dan_danh_muc=s["danh_muc"],
                co_review=(idx in (31, 32)),
                so_ban_that=(da_ban // 10 if idx <= 12 else 0),
            )
        )

    danh_muc_kem_so = [
        {
            "danh_muc": dm,
            "so_sach": dem_theo_dm.get(dm.ma, 0),
            "so_sach_dang_ban": dem_theo_dm.get(dm.ma, 0),
        }
        for dm in danh_muc_ds
    ]

    khach_mau = KhachHang(
        ma=1,
        ho_ten="Nguyễn Minh Anh",
        email="minhanh@example.com",
        dien_thoai="0909 123 456",
        dia_chi="45 Lý Tự Trọng, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
        mat_khau_bam="bam-gia",
        ngay_tao=moc - timedelta(days=15),
    )

    ma_giam_dau = goc_json.get("ma_giam_gia", [{}])[0]
    ma_giam_mau = MaGiamGia(
        ma=ma_giam_dau.get("ma", "CHAOHE"),
        kieu=ma_giam_dau.get("kieu", "phan_tram"),
        gia_tri=int(ma_giam_dau.get("gia_tri", 10)),
        don_toi_thieu=int(ma_giam_dau.get("don_toi_thieu", 100000)),
        het_han="2026-12-31",
        so_luot_toi_da=100,
        da_dung=12,
        dang_bat=True,
    )

    return {
        "moc": moc,
        "danh_muc_ds": danh_muc_ds,
        "dm_theo_ma": dm_theo_ma,
        "danh_muc_kem_so": danh_muc_kem_so,
        "sach_ds": sach_ds,
        "dg_goc_theo_sach": dg_goc_theo_sach,
        "khach_mau": khach_mau,
        "ma_giam_mau": ma_giam_mau,
    }


def tao_du_lieu_gia() -> dict:
    """Giữ hàm tương thích cho trang chủ."""
    kho = nap_kho_gia()
    return du_lieu_trang_chu(kho)


def bien_chung(
    kho: dict,
    *,
    khach: KhachHang | None = None,
    la_quan_ly: bool = False,
    so_trong_gio: int = 2,
    path: str = "/",
    args: dict | None = None,
) -> dict:
    return {
        "csrf": "xem-truoc-csrf-token",
        "khach": khach,
        "la_quan_ly": la_quan_ly,
        "so_trong_gio": so_trong_gio,
        "danh_muc_menu": kho["danh_muc_ds"],
        "request": GiaRequest(path=path, args=args),
    }


def du_lieu_trang_chu(kho: dict, *, khach: KhachHang | None = None) -> dict:
    sach_ds = kho["sach_ds"]
    ung_vien = [s for s in sach_ds if s.dang_ban and s.ton_kho > 0]
    ung_vien.sort(key=lambda s: (bool(s.anh_bia), s.gia_bia > s.gia, s.da_ban, s.diem_tb), reverse=True)
    noi_bat = ung_vien[0] if ung_vien else None

    da_dung = {noi_bat.ma} if noi_bat else set()

    def lay_khong_trung(ds, gioi_han):
        kq = []
        for s in ds:
            if s.ma not in da_dung:
                da_dung.add(s.ma)
                kq.append(s)
                if len(kq) == gioi_han:
                    break
        return kq

    con_lai = [s for s in sach_ds if s.ma not in da_dung]
    ban_chay_goc = sorted(con_lai, key=lambda s: (bool(s.anh_bia), s.da_ban), reverse=True)
    ban_chay = lay_khong_trung(ban_chay_goc, 8)
    tieu_diem = lay_khong_trung([s for s in ung_vien if s.anh_bia] + ung_vien, 3)
    uu_dai = lay_khong_trung(
        sorted([s for s in sach_ds if s.gia < s.gia_bia and s.ton_kho > 0],
               key=lambda s: (s.gia_bia - s.gia) / s.gia_bia, reverse=True),
        8,
    )
    sach_rv = lay_khong_trung([s for s in sach_ds if s.co_review], 2)
    goc_review = [
        {
            "sach": s,
            "trich": (
                "Cuốn sách mở ra góc nhìn rõ ràng và giàu suy ngẫm, dễ theo dõi ngay từ chương đầu. "
                "Đáng để giữ trên kệ đọc chậm qua nhiều buổi tối."
            ),
        }
        for s in sach_rv
    ]
    sach_moi = lay_khong_trung(sorted(sach_ds, key=lambda s: s.ngay_them, reverse=True), 8)
    vua_xem = lay_khong_trung(sach_ds, 4) if khach else []

    return {
        **bien_chung(kho, khach=khach, path="/"),
        "noi_bat": noi_bat,
        "tieu_diem": tieu_diem,
        "danh_muc": kho["danh_muc_kem_so"],
        "sach_moi": sach_moi,
        "ban_chay": ban_chay,
        "ten_khoi": "Bán chạy",
        "uu_dai": uu_dai,
        "goc_review": goc_review,
        "vua_xem": vua_xem,
    }


def tao_cac_trang(kho: dict) -> list[tuple[str, str, dict, list[tuple[str, str]]]]:
    """Danh sách (template_path, ten_tep_ra, context, flash_messages)."""
    sach_ds: list[Sach] = kho["sach_ds"]
    dm_ds: list[DanhMuc] = kho["danh_muc_ds"]
    dm_theo_ma: dict[int, DanhMuc] = kho["dm_theo_ma"]
    khach_mau: KhachHang = kho["khach_mau"]
    moc: datetime = kho["moc"]
    ma_giam_mau: MaGiamGia = kho["ma_giam_mau"]

    # 1. Chi tiết sách (ưu tiên sách có bìa ảnh thật để kiểm chứng cả bìa ảnh và review nhà sách)
    sach_co_anh = [s for s in sach_ds if s.anh_bia]
    sach_ct = sach_co_anh[0] if sach_co_anh else sach_ds[0]
    dm_ct = dm_theo_ma[sach_ct.ma_danh_muc]
    lien_quan = [s for s in sach_ds if s.ma_danh_muc == sach_ct.ma_danh_muc and s.ma != sach_ct.ma][:4]
    if len(lien_quan) < 4:
        lien_quan += [s for s in sach_ds if s.ma != sach_ct.ma and s not in lien_quan][: 4 - len(lien_quan)]

    bai_review_mau = BaiReviewXemTruoc(
        ma=1,
        ma_sach=sach_ct.ma,
        tieu_de=f"Vì sao «{sach_ct.tieu_de}» xứng đáng nằm trên kệ sách của bạn",
        noi_dung=(
            "Ngay từ những trang mở đầu, cuốn sách tạo nên một nhịp đọc điềm tĩnh nhưng lôi cuốn, "
            "đưa người đọc đi sâu vào bối cảnh tư tưởng và những câu hỏi lớn xoay quanh con người.\n\n"
            "Điểm đáng giá nhất nằm ở cách tác giả giữ sự cân bằng giữa chiều sâu học thuật và lối diễn đạt "
            "sáng rõ. Mỗi chương đều mở ra những lát cắt giàu gợi mở, đủ để bạn dừng lại ghi chú và đối chiếu "
            "với trải nghiệm của chính mình.\n\n"
            "Nhà Sách Tri Thức gợi ý cuốn sách này cho độc giả muốn tìm một bản đọc giàu suy ngẫm, "
            "có thể đọc chậm rãi qua nhiều buổi tối và quay lại nhiều lần."
        ),
        tac_gia_review="Ban Biên Tập",
        trang_thai=TrangThaiReview.DA_DUYET,
        tao_luc=moc - timedelta(days=3),
        duyet_luc=moc - timedelta(days=2),
        sach=sach_ct,
    )
    sach_rv_2 = sach_co_anh[1] if len(sach_co_anh) > 1 else sach_ds[1]
    ds_review_ql = [
        bai_review_mau,
        BaiReviewXemTruoc(
            ma=2,
            ma_sach=sach_rv_2.ma,
            tieu_de=f"Góc nhìn sắc sảo qua từng trang «{sach_rv_2.tieu_de}»",
            noi_dung=(
                "Một cuốn sách giúp người đọc tiếp cận chủ đề khó bằng ngôn ngữ gần gũi và mạch lập luận rõ ràng.\n\n"
                "Bản nháp đang chờ biên tập viên soát lại trích dẫn trước khi duyệt đăng công khai."
            ),
            tac_gia_review="Nhà Sách Tri Thức",
            trang_thai=TrangThaiReview.NHAP,
            tao_luc=moc - timedelta(hours=14),
            duyet_luc=None,
            sach=sach_rv_2,
        ),
        BaiReview(
            ma=3,
            ma_sach=sach_ds[0].ma,
            tieu_de="Ký ức tuổi thơ bền bỉ qua nhiều thế hệ bạn đọc",
            noi_dung=(
                "Tác phẩm quen thuộc với nhiều thế hệ độc giả Việt Nam nhờ giọng kể hóm hỉnh và giàu chất thơ.\n\n"
                "Đang hoàn thiện bản nháp giới thiệu."
            ),
            tac_gia_review="Nhà Sách Tri Thức",
            trang_thai=TrangThaiReview.NHAP,
            tao_luc=moc - timedelta(hours=5),
            duyet_luc=None,
        ),
    ]

    dg_mau = []
    for idx, d in enumerate(kho["dg_goc_theo_sach"].get(sach_ct.tieu_de, []), start=1):
        dg_mau.append(
            {
                "danh_gia": DanhGia(
                    ma=idx,
                    ma_sach=sach_ct.ma,
                    ma_khach=idx,
                    so_sao=int(d["so_sao"]),
                    noi_dung=chuan_nfc(d["noi_dung"]) or "",
                    tao_luc=moc - timedelta(days=idx * 2),
                    an=False,
                ),
                "ten_khach": chuan_nfc(d["ten_khach"]) or "Độc giả",
            }
        )
    dg_mau.append(
        {
            "danh_gia": DanhGia(
                ma=99,
                ma_sach=sach_ct.ma,
                ma_khach=khach_mau.ma,
                so_sao=5,
                noi_dung="Bản in rõ nét, giao hàng rất nhanh và đóng gói cẩn thận.",
                tao_luc=moc - timedelta(hours=6),
                an=False,
            ),
            "ten_khach": khach_mau.ho_ten,
        }
    )
    sach_ct_hien = replace(
        sach_ct,
        so_danh_gia=len(dg_mau),
        diem_tb=round(sum(m["danh_gia"].so_sao for m in dg_mau) / len(dg_mau), 1),
        so_ban_that=max(sach_ct.so_ban_that, 18),
    )

    # 2. Giỏ hàng mẫu (gồm cả sách có bìa ảnh thật và sách bìa SVG)
    sach_gio_1 = sach_co_anh[0] if sach_co_anh else sach_ds[0]
    sach_gio_2 = sach_ds[6]
    muc_gio = [
        {"sach": sach_gio_1, "so_luong": 2, "thanh_tien": sach_gio_1.gia * 2},
        {"sach": sach_gio_2, "so_luong": 1, "thanh_tien": sach_gio_2.gia},
    ]
    tam_tinh = sum(m["thanh_tien"] for m in muc_gio)
    giam_gia = int(tam_tinh * 10 // 100)
    sau_giam = tam_tinh - giam_gia
    phi_giao = 0 if sau_giam >= 300000 else 25000
    gio_day = XemGio(
        muc=muc_gio,
        tam_tinh=tam_tinh,
        ma_giam_gia=ma_giam_mau,
        giam_gia=giam_gia,
        phi_giao=phi_giao,
        tong=sau_giam + phi_giao,
        canh_bao=[],
    )
    gio_trong = XemGio(
        muc=[],
        tam_tinh=0,
        ma_giam_gia=None,
        giam_gia=0,
        phi_giao=0,
        tong=0,
        canh_bao=[],
    )

    # 3. Đơn hàng mẫu (chuyển khoản QR chưa thanh toán + các trạng thái khác cho lịch sử đơn)
    don_qr = DonHang(
        ma=101,
        ma_tra_cuu="K8M2P9Q4",
        ma_khach=khach_mau.ma,
        ho_ten=khach_mau.ho_ten,
        dien_thoai=khach_mau.dien_thoai,
        dia_chi=khach_mau.dia_chi,
        ghi_chu="Giao giờ hành chính, gọi trước 15 phút.",
        phuong_thuc=PhuongThucThanhToan.CHUYEN_KHOAN,
        da_thanh_toan=False,
        trang_thai=TrangThaiDon.CHO_XAC_NHAN,
        tam_tinh=tam_tinh,
        giam_gia=giam_gia,
        phi_giao=phi_giao,
        tong=sau_giam + phi_giao,
        ma_giam_gia=ma_giam_mau.ma,
        tao_luc=moc - timedelta(minutes=25),
        cap_nhat_luc=moc - timedelta(minutes=20),
        muc=[
            MucDon(
                sach_gio_1.ma, sach_gio_1.tieu_de, sach_gio_1.gia, 2,
                mau_bia=sach_gio_1.mau_bia, duong_dan_danh_muc=sach_gio_1.duong_dan_danh_muc,
                anh_bia=sach_gio_1.anh_bia, tac_gia=sach_gio_1.tac_gia,
            ),
            MucDon(
                sach_gio_2.ma, sach_gio_2.tieu_de, sach_gio_2.gia, 1,
                mau_bia=sach_gio_2.mau_bia, duong_dan_danh_muc=sach_gio_2.duong_dan_danh_muc,
                anh_bia=sach_gio_2.anh_bia, tac_gia=sach_gio_2.tac_gia,
            ),
        ],
    )
    don_giao = DonHang(
        ma=98,
        ma_tra_cuu="H3T7W1N5",
        ma_khach=khach_mau.ma,
        ho_ten=khach_mau.ho_ten,
        dien_thoai=khach_mau.dien_thoai,
        dia_chi=khach_mau.dia_chi,
        ghi_chu="",
        phuong_thuc=PhuongThucThanhToan.COD,
        da_thanh_toan=True,
        trang_thai=TrangThaiDon.HOAN_THANH,
        tam_tinh=sach_ds[1].gia + sach_ds[3].gia,
        giam_gia=0,
        phi_giao=25000,
        tong=sach_ds[1].gia + sach_ds[3].gia + 25000,
        ma_giam_gia=None,
        tao_luc=moc - timedelta(days=5),
        cap_nhat_luc=moc - timedelta(days=3),
        muc=[
            MucDon(sach_ds[1].ma, sach_ds[1].tieu_de, sach_ds[1].gia, 1),
            MucDon(sach_ds[3].ma, sach_ds[3].tieu_de, sach_ds[3].gia, 1),
        ],
    )

    ngan_hang_mau = {
        "ten": "Vietcombank — Chi nhánh TP.HCM",
        "so_tk": "0071 0012 3456 78",
        "chu_tk": "NHA SACH TRI THUC",
        "noi_dung_ck": "NS K8M2P9Q4",
    }
    ngan_hang_mo_phong = {
        "ten": "Mô phỏng — không chuyển tiền",
        "so_tk": "Không có tài khoản thật",
        "chu_tk": "Nhà sách trình diễn",
        "noi_dung_ck": f"NHASACH {don_qr.ma_tra_cuu}",
    }

    don_huy_hoan = DonHang(
        ma=97,
        ma_tra_cuu="R5V8C2X9",
        ma_khach=khach_mau.ma,
        ho_ten=khach_mau.ho_ten,
        dien_thoai=khach_mau.dien_thoai,
        dia_chi=khach_mau.dia_chi,
        ghi_chu="Khách yêu cầu đổi đơn khác.",
        phuong_thuc=PhuongThucThanhToan.CHUYEN_KHOAN,
        da_thanh_toan=True,
        da_hoan_tien=True,
        trang_thai=TrangThaiDon.DA_HUY,
        tam_tinh=sach_ds[2].gia * 2,
        giam_gia=0,
        phi_giao=25000,
        tong=sach_ds[2].gia * 2 + 25000,
        ma_giam_gia=None,
        tao_luc=moc - timedelta(days=7),
        cap_nhat_luc=moc - timedelta(days=6),
        muc=[MucDon(sach_ds[2].ma, sach_ds[2].tieu_de, sach_ds[2].gia, 2)],
    )
    don_da_tt_chuan_bi = DonHang(
        ma=100,
        ma_tra_cuu="B4D6F1J8",
        ma_khach=2,
        ho_ten="Trần Gia Bảo",
        dien_thoai="0912 888 999",
        dia_chi="12 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
        ghi_chu="Đóng gói kỹ giúp mình.",
        phuong_thuc=PhuongThucThanhToan.CHUYEN_KHOAN,
        da_thanh_toan=True,
        da_hoan_tien=False,
        trang_thai=TrangThaiDon.DANG_CHUAN_BI,
        tam_tinh=sach_ds[4].gia + sach_ds[5].gia,
        giam_gia=20000,
        phi_giao=0,
        tong=sach_ds[4].gia + sach_ds[5].gia - 20000,
        ma_giam_gia="GIAM20K",
        tao_luc=moc - timedelta(hours=8),
        cap_nhat_luc=moc - timedelta(hours=3),
        muc=[
            MucDon(sach_ds[4].ma, sach_ds[4].tieu_de, sach_ds[4].gia, 1),
            MucDon(sach_ds[5].ma, sach_ds[5].tieu_de, sach_ds[5].gia, 1),
        ],
    )

    khach_2 = KhachHang(
        ma=2,
        ho_ten="Trần Gia Bảo",
        email="giabao@example.com",
        dien_thoai="0912 888 999",
        dia_chi="12 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
        mat_khau_bam="bam-gia-2",
        ngay_tao=moc - timedelta(days=9),
    )

    # 4. Dữ liệu quản lý (doanh thu 30 ngày & 12 tháng, top 10, sắp hết, mã giảm giá, đánh giá)
    doanh_thu_ngay = [
        {
            "ngay": (moc - timedelta(days=29 - i)).strftime("%Y-%m-%d"),
            "tien": ((i * 7 + 5) % 11) * 145000 + (220000 if i % 4 == 0 else 80000),
        }
        for i in range(30)
    ]
    doanh_thu_thang = [
        {
            "thang": f"{moc.year if (moc.month - 11 + i) > 0 else moc.year - 1}-{((moc.month - 12 + i) % 12) + 1:02d}",
            "tien": (3200000 + ((i * 5 + 3) % 7) * 950000),
        }
        for i in range(12)
    ]
    top_ban_chay = [
        {"sach": s, "so_ban": max(12, s.da_ban // 4)}
        for s in sorted(sach_ds, key=lambda x: x.da_ban, reverse=True)[:10]
    ]
    sap_het_ds = [s for s in sach_ds if s.ton_kho <= 5]
    if len(sap_het_ds) < 3:
        sap_het_ds.append(replace(sach_ds[4], ton_kho=3))
        sap_het_ds.append(replace(sach_ds[7], ton_kho=5))

    ds_ma_giam = [
        ma_giam_mau,
        MaGiamGia("GIAM30K", "tien", 30000, 200000, "2026-12-15", 50, 18, True),
        MaGiamGia("TET2026", "phan_tram", 15, 250000, None, None, 41, False),
    ]
    ds_danh_gia_ql = [
        {"danh_gia": dg_mau[0]["danh_gia"], "sach": sach_ds[0], "khach": khach_mau},
        {
            "danh_gia": DanhGia(
                ma=102,
                ma_sach=sach_ds[1].ma,
                ma_khach=khach_2.ma,
                so_sao=4,
                noi_dung="Sách đẹp, giao hơi trễ 1 ngày nhưng vẫn hài lòng.",
                tao_luc=moc - timedelta(days=1),
                an=False,
            ),
            "sach": sach_ds[1],
            "khach": khach_2,
        },
        {
            "danh_gia": DanhGia(
                ma=103,
                ma_sach=sach_ds[2].ma,
                ma_khach=khach_2.ma,
                so_sao=2,
                noi_dung="Bình luận spam quảng cáo đã bị quản lý ẩn.",
                tao_luc=moc - timedelta(days=2),
                an=True,
            ),
            "sach": sach_ds[2],
            "khach": khach_2,
        },
    ]
    cua_hang_mau = {
        "ten": "Nhà Sách Tri Thức",
        "dia_chi": "Số 128 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh",
        "dien_thoai": "1900 6868",
    }
    danh_muc_ql = list(kho["danh_muc_kem_so"]) + [
        {
            "danh_muc": DanhMuc(ma=98, ten="Triết học", duong_dan="triet-hoc", thu_tu=9),
            "so_sach": 1,
            "so_sach_dang_ban": 0,
        },
        {
            "danh_muc": DanhMuc(ma=99, ten="Tâm lý học", duong_dan="tam-ly-hoc", thu_tu=10),
            "so_sach": 0,
            "so_sach_dang_ban": 0,
        },
    ]

    return [
        (
            "trang_chu.html",
            "trang_chu.html",
            du_lieu_trang_chu(kho),
            [],
        ),
        (
            "trang_chu.html",
            "trang_chu_da_dang_nhap.html",
            du_lieu_trang_chu(kho, khach=khach_mau),
            [("tot", Markup('Đã thêm «Dế Mèn phiêu lưu ký» vào giỏ. <a href="/gio">Xem giỏ hàng</a>.'))],
        ),
        (
            "danh_sach.html",
            "danh_sach.html",
            {
                **bien_chung(kho, path="/sach", args={"danh_muc": dm_ds[0].duong_dan}),
                "ket_qua": Trang(muc=(sach_co_anh[:6] + [s for s in sach_ds if not s.anh_bia][:6])[:12], trang=1, so_trang=3, tong=len(sach_ds)),
                "bo_loc": {
                    "q": "", "danh_muc": dm_ds[0].duong_dan, "tac_gia": "",
                    "gia_tu": "", "gia_den": "", "sap_xep": "moi",
                    "giam_gia": False, "con_hang": False, "co_review": False,
                },
                "danh_muc": dm_ds,
                "danh_muc_kem_dem": kho["danh_muc_kem_so"],
                "danh_muc_dang_chon": dm_ds[0],
            },
            [],
        ),
        (
            "danh_sach.html",
            "danh_sach_trong.html",
            {
                **bien_chung(kho, path="/sach", args={"q": "khong-ton-tai"}),
                "ket_qua": Trang(muc=[], trang=1, so_trang=0, tong=0),
                "bo_loc": {
                    "q": "khong-ton-tai", "danh_muc": "", "tac_gia": "",
                    "gia_tu": "", "gia_den": "", "sap_xep": None,
                    "giam_gia": False, "con_hang": False, "co_review": False,
                },
                "danh_muc": dm_ds,
                "danh_muc_kem_dem": kho["danh_muc_kem_so"],
                "danh_muc_dang_chon": None,
            },
            [],
        ),
        (
            "chi_tiet.html",
            "chi_tiet.html",
            {
                **bien_chung(kho, khach=khach_mau, path=f"/sach/{sach_ct.ma}"),
                "sach": sach_ct_hien,
                "danh_muc_sach": dm_ct,
                "bai_review": bai_review_mau,
                "danh_gia": dg_mau,
                "cung_tac_gia": sach_ds[1:3],
                "lien_quan": lien_quan,
                "vua_xem": sach_ds[4:8],
                "co_the_danh_gia": True,
                "danh_gia_cua_toi": dg_mau[-1]["danh_gia"],
            },
            [],
        ),
        (
            "chi_tiet.html",
            "chi_tiet_khong_review.html",
            {
                **bien_chung(kho, khach=khach_mau, path=f"/sach/{sach_ds[0].ma}"),
                "sach": sach_ds[0],
                "danh_muc_sach": dm_theo_ma[sach_ds[0].ma_danh_muc],
                "bai_review": None,
                "danh_gia": dg_mau,
                "cung_tac_gia": [],
                "lien_quan": lien_quan,
                "vua_xem": [],
                "co_the_danh_gia": False,
                "danh_gia_cua_toi": None,
            },
            [],
        ),
        (
            "gio_hang.html",
            "gio_hang.html",
            {
                **bien_chung(kho, so_trong_gio=3, path="/gio"),
                "gio": gio_day,
            },
            [],
        ),
        (
            "gio_hang.html",
            "gio_hang_trong.html",
            {
                **bien_chung(kho, so_trong_gio=0, path="/gio"),
                "gio": gio_trong,
            },
            [],
        ),
        (
            "gio_hang.html",
            "gio_hang_canh_bao.html",
            {
                **bien_chung(kho, so_trong_gio=3, path="/gio"),
                "gio": XemGio(
                    muc=[
                        {"sach": replace(sach_ds[0], ton_kho=1), "so_luong": 2, "thanh_tien": sach_ds[0].gia * 2},
                        {"sach": sach_ds[6], "so_luong": 1, "thanh_tien": sach_ds[6].gia},
                    ],
                    tam_tinh=tam_tinh,
                    ma_giam_gia=None,
                    giam_gia=0,
                    phi_giao=25000,
                    tong=tam_tinh + 25000,
                    canh_bao=[
                        f'{sach_ds[0].tieu_de} không còn đủ hàng.',
                        'Mã giảm giá "HETLUOT" đã hết lượt sử dụng.',
                    ],
                ),
            },
            [("loi", "Không thể áp dụng mã giảm giá đã nhập.")],
        ),
        (
            "dat_hang.html",
            "dat_hang.html",
            {
                **bien_chung(kho, khach=khach_mau, so_trong_gio=3, path="/dat-hang"),
                "gio": gio_day,
                "mac_dinh": {
                    "ho_ten": khach_mau.ho_ten,
                    "dien_thoai": khach_mau.dien_thoai,
                    "dia_chi": khach_mau.dia_chi,
                    "ghi_chu": "",
                    "phuong_thuc": "chuyen_khoan",
                },
                "ma_thao_tac": "op-dat-hang-mau-01",
                "ma_giam_gia": ma_giam_mau.ma,
                "loi": None,
                "loi_truong": {},
            },
            [],
        ),
        (
            "dat_hang.html",
            "dat_hang_loi.html",
            {
                **bien_chung(kho, khach=khach_mau, so_trong_gio=3, path="/dat-hang"),
                "gio": gio_day,
                "mac_dinh": {
                    "ho_ten": khach_mau.ho_ten,
                    "dien_thoai": "123",
                    "dia_chi": khach_mau.dia_chi,
                    "ghi_chu": "Giao buổi chiều",
                    "phuong_thuc": "cod",
                },
                "ma_thao_tac": "op-dat-hang-mau-02",
                "ma_giam_gia": "KHONGHOP",
                "loi": "Nhập số điện thoại Việt Nam gồm 10 chữ số.",
                "loi_truong": {
                    "dien_thoai": "Nhập số điện thoại Việt Nam gồm 10 chữ số.",
                    "ma_giam_gia": "Mã KHONGHOP không tồn tại.",
                },
            },
            [],
        ),
        (
            "don_hang.html",
            "don_hang.html",
            {
                **bien_chung(kho, khach=khach_mau, so_trong_gio=0, path=f"/don/{don_qr.ma_tra_cuu}"),
                "don": don_qr,
                "qr_svg": QR_SVG_MAU,
                "ngan_hang": ngan_hang_mau,
                "co_the_huy": True,
            },
            [("tot", "Đặt hàng thành công! Hãy lưu lại mã tra cứu bên dưới.")],
        ),
        (
            "don_hang.html",
            "don_hang_qr_mo_phong.html",
            {
                **bien_chung(kho, khach=khach_mau, so_trong_gio=0, path=f"/don/{don_qr.ma_tra_cuu}"),
                "don": don_qr,
                "qr_svg": QR_SVG_MAU,
                "ngan_hang": ngan_hang_mo_phong,
                "co_the_huy": True,
            },
            [],
        ),
        (
            "don_hang.html",
            "don_hang_da_huy_hoan_tien.html",
            {
                **bien_chung(kho, khach=khach_mau, so_trong_gio=0, path=f"/don/{don_huy_hoan.ma_tra_cuu}"),
                "don": don_huy_hoan,
                "qr_svg": None,
                "ngan_hang": ngan_hang_mau,
                "co_the_huy": False,
            },
            [],
        ),
        (
            "tra_cuu.html",
            "tra_cuu.html",
            {
                **bien_chung(kho, path="/tra-cuu", args={"ma": "K8M2P9Q4"}),
                "loi": None,
                "form": {"ma": "K8M2P9Q4", "dien_thoai": ""},
                "loi_truong": {},
            },
            [],
        ),
        (
            "tra_cuu.html",
            "tra_cuu_loi.html",
            {
                **bien_chung(kho, path="/tra-cuu"),
                "loi": "Mã tra cứu hoặc số điện thoại không khớp.",
                "form": {"ma": "ABC", "dien_thoai": "090912345"},
                "loi_truong": {
                    "ma": "Mã tra cứu gồm 8 chữ cái hoặc chữ số.",
                    "dien_thoai": "Nhập số điện thoại Việt Nam gồm 10 chữ số.",
                },
            },
            [],
        ),
        (
            "tai_khoan/dang_ky.html",
            "tai_khoan_dang_ky.html",
            {
                **bien_chung(kho, path="/dang-ky"),
                "form": {"ho_ten": "Trần Gia Bảo", "email": "giabao@example.com", "dien_thoai": "0912 888 999"},
                "loi_truong": {},
            },
            [],
        ),
        (
            "tai_khoan/dang_nhap.html",
            "tai_khoan_dang_nhap.html",
            {
                **bien_chung(kho, path="/dang-nhap"),
                "form": {"email": "minhanh@example.com"},
            },
            [("loi", "Email hoặc mật khẩu chưa đúng.")],
        ),
        (
            "tai_khoan/don_cua_toi.html",
            "tai_khoan_don_cua_toi.html",
            {
                **bien_chung(kho, khach=khach_mau, so_trong_gio=0, path="/tai-khoan"),
                "don": [don_qr, don_giao, don_huy_hoan],
                "ho_so": {
                    "ho_ten": khach_mau.ho_ten,
                    "dien_thoai": khach_mau.dien_thoai,
                    "dia_chi": khach_mau.dia_chi,
                },
                "loi_truong": {},
            },
            [],
        ),
        (
            "loi.html",
            "loi.html",
            {
                **bien_chung(kho, path="/duong-dan-la"),
                "ma_loi": 404,
                "tieu_de": "Không tìm thấy trang",
                "thong_bao": "Đường dẫn bạn truy cập không tồn tại hoặc cuốn sách đã bị gỡ khỏi kệ.",
            },
            [],
        ),
        (
            "loi.html",
            "loi_400.html",
            {
                **bien_chung(kho, path="/gio/them"),
                "ma_loi": 400,
                "tieu_de": "Phiên làm việc không hợp lệ",
                "thong_bao": "Mã bảo mật biểu mẫu đã hết hạn. Hãy tải lại trang và thử lại.",
            },
            [],
        ),
        # --- Các trang Quản lý (Đợt B) ---
        (
            "quan_ly/dang_nhap.html",
            "quan_ly_dang_nhap.html",
            {
                **bien_chung(kho, path="/quan-ly/dang-nhap"),
            },
            [],
        ),
        (
            "quan_ly/tong_quan.html",
            "quan_ly_tong_quan.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/"),
                "the": {
                    "doanh_thu_thang": doanh_thu_thang[-1]["tien"],
                    "don_cho_xac_nhan": 4,
                    "sach_sap_het": len(sap_het_ds),
                    "so_khach": 28,
                },
                "doanh_thu_ngay": doanh_thu_ngay,
                "doanh_thu_thang": doanh_thu_thang,
                "ban_chay": top_ban_chay,
                "sap_het": sap_het_ds,
            },
            [],
        ),
        (
            "quan_ly/sach.html",
            "quan_ly_sach.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/sach"),
                "ket_qua": Trang(
                    muc=[*(sach_co_anh[:4]), replace(sach_ds[1], dang_ban=False), *sach_ds[2:7]],
                    trang=1,
                    so_trang=3,
                    tong=len(sach_ds),
                ),
                "danh_muc": dm_ds,
                "bo_loc": {"q": "", "danh_muc": "", "loc": ""},
                "loc": "",
            },
            [],
        ),
        (
            "quan_ly/sua_sach.html",
            "quan_ly_sua_sach.html",
            {
                **bien_chung(kho, la_quan_ly=True, path=f"/quan-ly/sach/{sach_ct.ma}/sua"),
                "sach": sach_ct,
                "danh_muc": dm_ds,
                "form": {},
                "ma_thao_tac": "op-sua-sach-01",
                "loi_truong": {},
            },
            [],
        ),
        (
            "quan_ly/sua_sach.html",
            "quan_ly_them_sach.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/sach/moi"),
                "sach": None,
                "danh_muc": dm_ds,
                "form": {},
                "ma_thao_tac": "op-them-sach-01",
                "loi_truong": {},
            },
            [],
        ),
        (
            "quan_ly/danh_muc.html",
            "quan_ly_danh_muc.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/danh-muc"),
                "danh_muc": danh_muc_ql,
            },
            [],
        ),
        (
            "quan_ly/don.html",
            "quan_ly_don.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/don"),
                "ket_qua": Trang(muc=[don_qr, don_da_tt_chuan_bi, don_giao, don_huy_hoan], trang=1, so_trang=1, tong=4),
                "loc": None,
                "cac_trang_thai": list(TrangThaiDon),
                "q": "",
            },
            [],
        ),
        (
            "quan_ly/chi_tiet_don.html",
            "quan_ly_chi_tiet_don.html",
            {
                **bien_chung(kho, la_quan_ly=True, path=f"/quan-ly/don/{don_qr.ma}"),
                "don": don_qr,
                "buoc_tiep": [TrangThaiDon.DANG_CHUAN_BI, TrangThaiDon.DA_HUY],
            },
            [],
        ),
        (
            "quan_ly/chi_tiet_don.html",
            "quan_ly_chi_tiet_don_da_tt.html",
            {
                **bien_chung(kho, la_quan_ly=True, path=f"/quan-ly/don/{don_da_tt_chuan_bi.ma}"),
                "don": don_da_tt_chuan_bi,
                "buoc_tiep": [TrangThaiDon.DANG_GIAO, TrangThaiDon.DA_HUY],
            },
            [],
        ),
        (
            "quan_ly/hoa_don.html",
            "quan_ly_hoa_don.html",
            {
                **bien_chung(kho, la_quan_ly=True, path=f"/quan-ly/don/{don_qr.ma}/hoa-don"),
                "don": don_qr,
                "cua_hang": cua_hang_mau,
            },
            [],
        ),
        (
            "quan_ly/khach_hang.html",
            "quan_ly_khach_hang.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/khach-hang"),
                "khach_hang": [
                    {"khach": khach_mau, "so_don": 3, "tong_chi": don_qr.tong + don_giao.tong},
                    {"khach": khach_2, "so_don": 1, "tong_chi": don_da_tt_chuan_bi.tong},
                ],
            },
            [],
        ),
        (
            "quan_ly/ma_giam_gia.html",
            "quan_ly_ma_giam_gia.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/ma-giam-gia"),
                "ma_giam_gia": ds_ma_giam,
            },
            [],
        ),
        (
            "quan_ly/danh_gia.html",
            "quan_ly_danh_gia.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/danh-gia"),
                "danh_gia": ds_danh_gia_ql,
            },
            [],
        ),
        (
            "quan_ly/review.html",
            "quan_ly_review.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/review"),
                "bai_review": ds_review_ql,
                "loc": "",
            },
            [],
        ),
        (
            "quan_ly/tao_review.html",
            "quan_ly_tao_review.html",
            {
                **bien_chung(kho, la_quan_ly=True, path="/quan-ly/review/moi"),
                "form": {"tac_gia_review": "Nhà Sách Tri Thức"},
                "loi_truong": {},
                "sach_chua_co_review": sach_ds[:3],
            },
            [],
        ),
        (
            "quan_ly/sua_review.html",
            "quan_ly_sua_review.html",
            {
                **bien_chung(kho, la_quan_ly=True, path=f"/quan-ly/review/{ds_review_ql[1].ma}/sua"),
                "bai_review": ds_review_ql[1],
                "form": {},
            },
            [],
        ),
    ]


def liet_ke_template_can_phu() -> set[str]:
    ket_qua: set[str] = set()
    for p in THU_MUC_TEMPLATE.rglob("*.html"):
        rel = p.relative_to(THU_MUC_TEMPLATE).as_posix()
        if p.name.startswith("_") or rel == "base.html":
            continue
        ket_qua.add(rel)
    return ket_qua


def dung_xem_truoc() -> int:
    kho = nap_kho_gia()
    cac_trang = tao_cac_trang(kho)

    # Đảm bảo không bỏ sót template nào trong templates/ (trừ _ macro và base.html)
    da_phu = {tpl for tpl, _, _, _ in cac_trang}
    can_phu = liet_ke_template_can_phu()
    thieu = sorted(can_phu - da_phu)
    if thieu:
        print("LOI: Co template chua duoc dung trong xem_truoc.py:", ", ".join(thieu), file=sys.stderr)
        return 1

    env = Environment(
        loader=FileSystemLoader(str(THU_MUC_TEMPLATE)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["tien"] = bo_loc_tien
    env.filters["ngay"] = bo_loc_ngay
    env.globals["url_for"] = gia_url_for

    THU_MUC_RA.mkdir(parents=True, exist_ok=True)

    # Kiểm tra riêng base.html cũng dựng sạch với StrictUndefined
    env.globals["get_flashed_messages"] = lambda with_categories=False: []
    env.get_template("base.html").render(**bien_chung(kho))

    so_loi = 0
    for tpl_path, ten_ra, ctx, flashes in cac_trang:
        env.globals["get_flashed_messages"] = (
            lambda with_categories=False, _fl=flashes: _fl if with_categories else [m for _, m in _fl]
        )
        try:
            html = env.get_template(tpl_path).render(**ctx)
        except Exception as exc:
            print(f"LOI khi dung {tpl_path} -> {ten_ra}: {type(exc).__name__}: {exc}", file=sys.stderr)
            so_loi += 1
            continue

        tep_ra = THU_MUC_RA / ten_ra
        tep_ra.write_text(html, encoding="utf-8")
        print(f"OK {tpl_path} -> xem_truoc/{ten_ra} ({tep_ra.stat().st_size} bytes)")

    if so_loi:
        print(f"TONG KET: {so_loi} trang loi.", file=sys.stderr)
        return 1
    print(f"TONG KET: Da dung thanh cong {len(cac_trang)} ban xem truoc ({len(da_phu)} template).")
    return 0


if __name__ == "__main__":
    sys.exit(dung_xem_truoc())
