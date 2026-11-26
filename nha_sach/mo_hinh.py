"""Các đối tượng của cửa hàng, độc lập với Flask và nơi lưu dữ liệu."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum
import re
import unicodedata

from .loi import LoiNghiepVu


class TrangThaiDon(StrEnum):
    CHO_XAC_NHAN = "cho_xac_nhan"
    DANG_CHUAN_BI = "dang_chuan_bi"
    DANG_GIAO = "dang_giao"
    HOAN_THANH = "hoan_thanh"
    DA_HUY = "da_huy"

    @property
    def nhan(self):
        return {
            self.CHO_XAC_NHAN: "Chờ xác nhận",
            self.DANG_CHUAN_BI: "Đang chuẩn bị",
            self.DANG_GIAO: "Đang giao",
            self.HOAN_THANH: "Hoàn thành",
            self.DA_HUY: "Đã hủy",
        }[self]

    def buoc_tiep(self):
        return {
            self.CHO_XAC_NHAN: (self.DANG_CHUAN_BI, self.DA_HUY),
            self.DANG_CHUAN_BI: (self.DANG_GIAO, self.DA_HUY),
            self.DANG_GIAO: (self.HOAN_THANH,),
        }.get(self, ())


class PhuongThuc(StrEnum):
    COD = "cod"
    CHUYEN_KHOAN = "chuyen_khoan"

    @property
    def nhan(self):
        return {
            self.COD: "Trả tiền khi nhận hàng",
            self.CHUYEN_KHOAN: "Chuyển khoản",
        }[self]


class PhuongThucThanhToan(ABC):
    @abstractmethod
    def duoc_giao(self, da_thanh_toan):
        """Xác định đơn có thể giao ở trạng thái thanh toán hiện tại."""

    @abstractmethod
    def can_qr(self):
        """Xác định phương thức dùng QR để nhận tiền."""

    @abstractmethod
    def thanh_toan_khi_hoan_thanh(self, da_thanh_toan):
        """Trả trạng thái thanh toán sau khi giao xong."""

    def can_hoan_tien_khi_huy(self, da_thanh_toan):
        # Cả hai phương thức đều phải hoàn khoản đã thu nếu hủy.
        return da_thanh_toan


class ThanhToanCOD(PhuongThucThanhToan):
    def duoc_giao(self, da_thanh_toan):
        return True

    def can_qr(self):
        return False

    def thanh_toan_khi_hoan_thanh(self, da_thanh_toan):
        return True


class ThanhToanChuyenKhoan(PhuongThucThanhToan):
    def duoc_giao(self, da_thanh_toan):
        return da_thanh_toan

    def can_qr(self):
        return True

    def thanh_toan_khi_hoan_thanh(self, da_thanh_toan):
        return da_thanh_toan


_CHINH_SACH_THANH_TOAN = {
    PhuongThuc.COD: ThanhToanCOD(),
    PhuongThuc.CHUYEN_KHOAN: ThanhToanChuyenKhoan(),
}


def chinh_sach_thanh_toan(phuong_thuc):
    return _CHINH_SACH_THANH_TOAN[phuong_thuc]


@dataclass
class DanhMuc:
    ma: int
    ten: str
    duong_dan: str
    thu_tu: int


@dataclass(frozen=True)
class BiaSach:
    dong_tieu_de: tuple[str, ...]
    co_chu: int
    mau_chu: str
    mau_phu: str
    khuon: str

    @staticmethod
    def do_sang(mau):
        rgb = [int(mau[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        tuyen_tinh = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return sum(a * b for a, b in zip(tuyen_tinh, (0.2126, 0.7152, 0.0722), strict=True))

    @classmethod
    def tao(cls, tieu_de, mau_bia, duong_dan_danh_muc: str | None):
        if duong_dan_danh_muc is not None and not isinstance(duong_dan_danh_muc, str):
            raise TypeError("Danh mục bìa phải là slug dạng chuỗi hoặc None.")
        dong = []
        hien_tai = ""
        for tu in (tieu_de or "Sách chưa đặt tên").split():
            if hien_tai and len(hien_tai) + len(tu) + 1 > 15:
                dong.append(hien_tai)
                hien_tai = ""
            hien_tai = f"{hien_tai} {tu}".strip()
        if hien_tai:
            dong.append(hien_tai)
        if len(dong) > 4:
            dong = dong[:3] + [dong[3][:13] + "…"]

        mau_bia = mau_bia or "#2b4c7e"
        nen = cls.do_sang(mau_bia)
        mau = "#ffffff" if 1.05 / (nen + 0.05) >= 4.5 else "#1a1a1a"
        # Một số tông trung gian cần chữ đen để đạt tương phản trên màu nền đã lưu.
        if mau == "#1a1a1a" and (nen + 0.05) / (cls.do_sang(mau) + 0.05) < 4.5:
            mau = "#000000"
        khuon = {
            "van-hoc": "co_dien", "kinh-te": "hien_dai", "ky-nang-song": "ky_nang",
            "thieu-nhi": "thieu_nhi", "khoa-hoc": "hien_dai", "lich-su": "co_dien",
            "nuoi-day-con": "ky_nang", "tieu-thuyet": "co_dien",
        }.get(duong_dan_danh_muc, "hien_dai")
        co_chu = {3: 20, 4: 18}.get(len(dong), 23)
        return cls(tuple(dong), co_chu, mau, mau, khuon)


class SoDienThoai:
    @staticmethod
    def chuan_hoa(gia_tri):
        so = re.sub(r"[\s.()\-]", "", gia_tri)
        if so.startswith("+84"):
            so = "0" + so[3:]
        elif so.startswith("84"):
            so = "0" + so[2:]
        return so if re.fullmatch(r"0[0-9]{9}", so) else None


class ChinhSachGiaoHang:
    PHI = 25000
    NGUONG_MIEN_PHI = 300000

    def con_thieu(self, sau_giam):
        return max(0, self.NGUONG_MIEN_PHI - sau_giam)

    def tinh_phi(self, sau_giam, co_hang=True):
        return self.PHI if co_hang and self.con_thieu(sau_giam) else 0


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
    da_ban: int = 0
    diem_tb: float = 0
    so_danh_gia: int = 0
    duong_dan_danh_muc: str | None = None
    co_review: bool = False
    so_ban_that: int = 0

    @property
    def bia(self):
        return BiaSach.tao(self.tieu_de, self.mau_bia, self.duong_dan_danh_muc)


@dataclass
class KhachHang:
    ma: int
    ho_ten: str
    email: str
    dien_thoai: str
    dia_chi: str
    mat_khau_bam: str = field(repr=False)
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
    def bia(self):
        if self.mau_bia:
            return BiaSach.tao(self.tieu_de, self.mau_bia, self.duong_dan_danh_muc)
        # Giữ bảng màu dự phòng của template cho mục đơn không còn sách liên kết.
        bang_mau = ("#2e7d32", "#1565c0", "#00695c", "#9a3412",
                    "#4527a0", "#37474f", "#6a1b9a", "#1e3a5f")
        return BiaSach.tao(self.tieu_de, bang_mau[self.ma_sach % len(bang_mau)], None)

    @property
    def thanh_tien(self):
        return self.don_gia * self.so_luong


@dataclass
class DonHang:
    ma: int
    ma_tra_cuu: str
    ma_khach: int | None
    ho_ten: str
    dien_thoai: str
    dia_chi: str
    ghi_chu: str
    phuong_thuc: PhuongThuc
    da_thanh_toan: bool
    da_hoan_tien: bool
    trang_thai: TrangThaiDon
    tam_tinh: int
    giam_gia: int
    phi_giao: int
    tong: int
    ma_giam_gia: str | None
    tao_luc: datetime
    cap_nhat_luc: datetime
    muc: list[MucDon] = field(default_factory=list)

    def buoc_hop_le(self):
        return tuple(
            buoc for buoc in self.trang_thai.buoc_tiep()
            if buoc != TrangThaiDon.DANG_GIAO
            or chinh_sach_thanh_toan(self.phuong_thuc).duoc_giao(self.da_thanh_toan)
        )

    def khach_co_the_huy(self):
        return not self.da_thanh_toan and TrangThaiDon.DA_HUY in self.buoc_hop_le()

    def chuyen_sang(self, trang_thai, *, da_hoan_tien=False, khach_huy=False):
        try:
            trang_thai = TrangThaiDon(trang_thai)
        except ValueError as exc:
            raise LoiNghiepVu("Trạng thái đơn không hợp lệ.") from exc
        if khach_huy and (trang_thai != TrangThaiDon.DA_HUY or not self.khach_co_the_huy()):
            raise LoiNghiepVu("Đơn hàng này không thể tự hủy.")
        if trang_thai not in self.buoc_hop_le():
            if trang_thai == TrangThaiDon.DANG_GIAO and trang_thai in self.trang_thai.buoc_tiep():
                raise LoiNghiepVu("Hãy xác nhận đã nhận chuyển khoản trước khi giao.")
            raise LoiNghiepVu("Không thể chuyển sang trạng thái đã chọn.")
        chinh_sach = chinh_sach_thanh_toan(self.phuong_thuc)
        hoan_tien = (
            trang_thai == TrangThaiDon.DA_HUY and chinh_sach.can_hoan_tien_khi_huy(self.da_thanh_toan)
        )
        if hoan_tien and not da_hoan_tien:
            raise LoiNghiepVu("Hãy xác nhận đã hoàn tiền trước khi hủy.")
        thanh_toan = self.da_thanh_toan
        if trang_thai == TrangThaiDon.HOAN_THANH:
            thanh_toan = chinh_sach.thanh_toan_khi_hoan_thanh(thanh_toan)
        return replace(
            self, trang_thai=trang_thai, da_thanh_toan=thanh_toan, da_hoan_tien=hoan_tien,
        )


class QuyTacGiamGia(ABC):
    @abstractmethod
    def tinh_giam(self, tam_tinh, gia_tri):
        """Tính mức giảm trước khi áp giới hạn theo giá trị đơn."""

    def gia_tri_hop_le(self, gia_tri):
        return gia_tri >= 1


class GiamPhanTram(QuyTacGiamGia):
    def tinh_giam(self, tam_tinh, gia_tri):
        return tam_tinh * gia_tri // 100

    def gia_tri_hop_le(self, gia_tri):
        return super().gia_tri_hop_le(gia_tri) and gia_tri <= 100


class GiamSoTien(QuyTacGiamGia):
    def tinh_giam(self, tam_tinh, gia_tri):
        return gia_tri


_QUY_TAC_GIAM_GIA = {"phan_tram": GiamPhanTram(), "tien": GiamSoTien()}


def quy_tac_giam_gia(kieu):
    try:
        return _QUY_TAC_GIAM_GIA[kieu]
    except KeyError as exc:
        raise ValueError("Kiểu giảm giá không hợp lệ.") from exc


@dataclass
class MaGiamGia:
    ma: str
    kieu: str
    gia_tri: int
    don_toi_thieu: int
    het_han: date | None
    so_luot_toi_da: int | None
    da_dung: int
    dang_bat: bool

    def tinh_giam(self, tam_tinh, hom_nay):
        if self.ly_do(tam_tinh, hom_nay):
            return None
        muc_giam = quy_tac_giam_gia(self.kieu).tinh_giam(tam_tinh, self.gia_tri)
        return min(tam_tinh, muc_giam)

    def ly_do(self, tam_tinh, hom_nay):
        if not self.dang_bat:
            return f"Mã {self.ma} hiện không hoạt động."
        if self.het_han is not None and self.het_han < hom_nay:
            return f"Mã {self.ma} đã hết hạn."
        if self.so_luot_toi_da is not None and self.da_dung >= self.so_luot_toi_da:
            return f"Mã {self.ma} đã hết lượt."
        if tam_tinh < self.don_toi_thieu:
            them = f"{self.don_toi_thieu - tam_tinh:,}".replace(",", ".")
            return f"Cần mua thêm {them} đ để dùng mã {self.ma}."
        return None


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


def khoa_tim(s):
    s = unicodedata.normalize("NFD", s.casefold().replace("đ", "d"))
    return "".join(c for c in s if not unicodedata.combining(c))

@dataclass(frozen=True)
class DanhMucDemSach:
    danh_muc: DanhMuc
    so_sach: int
    so_sach_dang_ban: int


@dataclass(frozen=True)
class KhachTongHop:
    khach: KhachHang
    so_don: int
    tong_chi: int


@dataclass(frozen=True)
class DanhGiaCongKhai:
    danh_gia: DanhGia
    ten_khach: str


@dataclass(frozen=True)
class DanhGiaQuanLy:
    danh_gia: DanhGia
    sach: Sach
    khach: KhachHang


@dataclass(frozen=True)
class DongXuatDon:
    ma_tra_cuu: str
    ho_ten: str
    dien_thoai: str
    dia_chi: str
    trang_thai: TrangThaiDon
    phuong_thuc: PhuongThuc
    tam_tinh: int
    giam_gia: int
    phi_giao: int
    tong: int
    tao_luc: datetime


@dataclass(frozen=True)
class DoanhThuNgay:
    ngay: date
    tien: int


class TrangThaiReview(StrEnum):
    NHAP = "nhap"
    DA_DUYET = "da_duyet"


@dataclass(frozen=True)
class SachCuaReview:
    tieu_de: str
    tac_gia: str
    anh_bia: str | None


@dataclass
class BaiReview:
    ma: int
    ma_sach: int
    tieu_de: str
    noi_dung: str
    tac_gia_review: str
    trang_thai: TrangThaiReview
    tao_luc: datetime
    duyet_luc: datetime | None
    sach: SachCuaReview | None = None
