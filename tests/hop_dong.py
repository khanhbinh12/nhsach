"""Hợp đồng biến theo route và ca render."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ca:
    duong_dan: str
    tep: str
    bien: str = ""
    ma: int = 200


CHUNG = {"csrf", "khach", "la_quan_ly", "so_trong_gio", "danh_muc_menu", "request"}

KHACH = (
    Ca("/", "trang_chu.html", "sach_moi ban_chay danh_muc noi_bat tieu_diem uu_dai goc_review ten_khoi vua_xem"),
    Ca("/sach", "danh_sach.html", "ket_qua bo_loc danh_muc danh_muc_dang_chon danh_muc_kem_dem"),
    Ca("/sach?q=khong-tim-thay", "danh_sach.html", "ket_qua bo_loc danh_muc danh_muc_dang_chon danh_muc_kem_dem"),
    Ca("/sach/1", "chi_tiet.html", "sach danh_gia lien_quan co_the_danh_gia danh_gia_cua_toi danh_muc_sach bai_review cung_tac_gia vua_xem"),
    Ca("/sach/9999", "loi.html", "ma_loi tieu_de thong_bao", 404),
    Ca("/gio", "gio_hang.html", "gio"),
    Ca("/dat-hang", "dat_hang.html", "gio mac_dinh ma_thao_tac loi loi_truong ma_giam_gia"),
    Ca("/tra-cuu", "tra_cuu.html", "loi form loi_truong"),
    Ca("/don/{ma_tra_cuu}", "don_hang.html", "don qr_svg ngan_hang co_the_huy"),
    Ca("/dang-ky", "tai_khoan/dang_ky.html", "form loi_truong"),
    Ca("/dang-nhap", "tai_khoan/dang_nhap.html", "form"),
    Ca("/tai-khoan", "tai_khoan/don_cua_toi.html", "don ho_so loi_truong"),
)

QUAN_LY = (
    Ca("/quan-ly/dang-nhap", "quan_ly/dang_nhap.html"),
    Ca("/quan-ly/", "quan_ly/tong_quan.html", "the doanh_thu_ngay doanh_thu_thang ban_chay sap_het"),
    Ca("/quan-ly/sach", "quan_ly/sach.html", "ket_qua danh_muc bo_loc loc"),
    Ca("/quan-ly/sach/moi", "quan_ly/sua_sach.html", "sach danh_muc form ma_thao_tac loi_truong"),
    Ca("/quan-ly/sach/1/sua", "quan_ly/sua_sach.html", "sach danh_muc form ma_thao_tac loi_truong"),
    Ca("/quan-ly/danh-muc", "quan_ly/danh_muc.html", "danh_muc"),
    Ca("/quan-ly/don", "quan_ly/don.html", "ket_qua loc cac_trang_thai q"),
    Ca("/quan-ly/don/1", "quan_ly/chi_tiet_don.html", "don buoc_tiep"),
    Ca("/quan-ly/don/1/hoa-don", "quan_ly/hoa_don.html", "don cua_hang"),
    Ca("/quan-ly/khach-hang", "quan_ly/khach_hang.html", "khach_hang"),
    Ca("/quan-ly/ma-giam-gia", "quan_ly/ma_giam_gia.html", "ma_giam_gia"),
    Ca("/quan-ly/danh-gia", "quan_ly/danh_gia.html", "danh_gia"),
    Ca("/quan-ly/review/moi", "quan_ly/tao_review.html", "form loi_truong sach_chua_co_review"),
)

LOI = (
    Ca("/dat-hang", "dat_hang.html", "gio mac_dinh ma_thao_tac loi loi_truong ma_giam_gia", 400),
    Ca("/tra-cuu", "tra_cuu.html", "loi form loi_truong"),
    Ca("/gio/them", "loi.html", "ma_loi tieu_de thong_bao", 400),
)
