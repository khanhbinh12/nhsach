"""Đọc và kiểm tra dữ liệu mẫu trước khi ghi cơ sở dữ liệu."""
from datetime import timedelta
import json
import re
from secrets import token_urlsafe

from werkzeug.security import generate_password_hash

from .dong_ho import DongHo
from .kho import DiChuyenLuocDo, KhoDanhGia, KhoDanhMuc, KhoDonHang, KhoDuLieuMau, KhoKhachHang, KhoMaGiamGia, KhoSach
from .mo_hinh import ChinhSachGiaoHang, MucDon, PhuongThuc, TrangThaiDon


def doc_du_lieu_mau(duong_dan):
    with open(duong_dan, encoding="utf-8") as tep:
        du_lieu = json.load(tep)
    danh_muc = du_lieu["danh_muc"]
    sach = du_lieu["sach"]
    ma_giam_gia = du_lieu["ma_giam_gia"]
    danh_gia = du_lieu["danh_gia"]
    if not danh_muc or not sach or not ma_giam_gia:
        raise ValueError("Dữ liệu mẫu cần danh mục, sách và mã giảm giá.")
    slug = {muc["duong_dan"] for muc in danh_muc}
    if len(slug) != len(danh_muc):
        raise ValueError("Danh mục mẫu bị trùng slug.")
    tieu_de = {item["tieu_de"] for item in sach}
    if len(tieu_de) != len(sach):
        raise ValueError("Sách mẫu bị trùng tiêu đề.")
    for item in sach:
        if item["danh_muc"] not in slug or not 0 <= item["gia"] <= item["gia_bia"]:
            raise ValueError(f"Danh mục hoặc giá không hợp lệ: {item['tieu_de']}")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", item["mau_bia"]):
            raise ValueError(f"Màu bìa không hợp lệ: {item['tieu_de']}")
    for item in danh_gia:
        if item["tieu_de_sach"] not in tieu_de or not 1 <= item["so_sao"] <= 5:
            raise ValueError(f"Đánh giá không hợp lệ: {item['tieu_de_sach']}")
    return du_lieu


class NapDuLieuMau:
    def __init__(self, csdl, dong_ho=None):
        self.csdl = csdl
        self.dong_ho = dong_ho if dong_ho is not None else DongHo()

    def nap(self, duong_dan):
        du_lieu = doc_du_lieu_mau(duong_dan)
        hom_nay = self.dong_ho.bay_gio()
        sach_cu = [item for item in du_lieu["sach"] if not item.get("ebook_mau")]
        ebook = [item for item in du_lieu["sach"] if item.get("ebook_mau")]
        if not sach_cu:
            raise ValueError("Không có sách mẫu gốc.")
        with self.csdl.giao_dich() as conn:
            dau = KhoDuLieuMau(conn).ghi_nhan()
            if dau:
                sach = self._danh_muc_va_sach(conn, du_lieu["danh_muc"], sach_cu, hom_nay)
                self._ma_giam_gia(conn, du_lieu["ma_giam_gia"])
                self._don_va_danh_gia(conn, du_lieu["danh_gia"], sach, hom_nay)
                self._don_dang_xu_ly(conn, sach, hom_nay)
            them = bool(ebook) and KhoDuLieuMau(conn).ghi_nhan("ebook_viec04")
            if them:
                self._danh_muc_va_sach(conn, du_lieu["danh_muc"], ebook, hom_nay)
                DiChuyenLuocDo.nap_noi_dung_demo(conn)
        return dau or them

    @staticmethod
    def _danh_muc_va_sach(conn, cac_muc, cac_sach, hom_nay):
        kho_danh_muc = KhoDanhMuc(conn)
        da_co = {muc.duong_dan for muc in kho_danh_muc.danh_sach()}
        for thu_tu, muc in enumerate(cac_muc, 1):
            if muc["duong_dan"] not in da_co:
                kho_danh_muc.them(muc["ten"], muc["duong_dan"], thu_tu)
        danh_muc = {muc.duong_dan: muc.ma for muc in kho_danh_muc.danh_sach()}
        kho_sach = KhoSach(conn)
        sach = {}
        for item in cac_sach:
            ma = kho_sach.luu(dict(
                item, ma_danh_muc=danh_muc[item["danh_muc"]], ngay_them=hom_nay.isoformat(),
                anh_bia=item.get("anh_bia"), dang_ban=True,
            ))
            sach[item["tieu_de"]] = (ma, item["gia"])
        return sach

    @staticmethod
    def _ma_giam_gia(conn, danh_sach):
        kho_ma = KhoMaGiamGia(conn)
        for item in danh_sach:
            if not kho_ma.them(dict(het_han=None, so_luot_toi_da=None) | item):
                raise ValueError(f"Mã giảm giá mẫu trùng: {item['ma']}")

    def _don_va_danh_gia(self, conn, danh_sach, sach, hom_nay):
        kho_khach, kho_don, kho_danh_gia = KhoKhachHang(conn), KhoDonHang(conn), KhoDanhGia(conn)
        mat_khau_bam = generate_password_hash(token_urlsafe(32))
        khach = {}
        for index, item in enumerate(danh_sach, 1):
            ten = item["ten_khach"]
            if ten not in khach:
                khach[ten] = kho_khach.them(
                    ten, f"khach-mau-{index}@example.invalid", "0900000000",
                    mat_khau_bam, hom_nay, dia_chi="Địa chỉ mẫu",
                ).ma
            tieu_de = item["tieu_de_sach"]
            luc = hom_nay - timedelta(days=(index - 1) * 2)
            don = self._them_don(
                kho_don, tieu_de, sach[tieu_de], luc, TrangThaiDon.HOAN_THANH,
                f"du-lieu-mau-{index}", ten, khach[ten],
            )
            kho_don.xac_nhan_thanh_toan(don.ma, luc)
            kho_danh_gia.luu(sach[tieu_de][0], khach[ten], item["so_sao"], item["noi_dung"], luc)

    def _don_dang_xu_ly(self, conn, sach, hom_nay):
        kho_don, kho_sach = KhoDonHang(conn), KhoSach(conn)
        trang_thai = (TrangThaiDon.CHO_XAC_NHAN, TrangThaiDon.DANG_CHUAN_BI, TrangThaiDon.DANG_GIAO)
        for index, (tt, tieu_de) in enumerate(zip(trang_thai, sach), 1):
            if not kho_sach.tru_ton(sach[tieu_de][0], 1):
                raise ValueError(f"Không đủ tồn để nạp đơn mẫu cho {tieu_de}.")
            self._them_don(
                kho_don, tieu_de, sach[tieu_de], hom_nay - timedelta(days=index),
                tt, f"du-lieu-mau-dang-xu-ly-{index}", "Khách vãng lai mẫu",
            )

    @staticmethod
    def _them_don(kho, tieu_de, sach, luc, trang_thai, ma_thao_tac, ten, ma_khach=None):
        ma_sach, gia = sach
        phi_giao = ChinhSachGiaoHang().tinh_phi(gia)
        return kho.them(
            dict(
                ma_tra_cuu=kho.tao_ma_tra_cuu(), ma_khach=ma_khach, ho_ten=ten,
                dien_thoai="0900000000", dia_chi="Địa chỉ mẫu", ghi_chu="Đơn mẫu",
                phuong_thuc=PhuongThuc.COD, trang_thai=trang_thai, tam_tinh=gia, giam_gia=0,
                phi_giao=phi_giao, tong=gia + phi_giao, ma_giam_gia=None,
                tao_luc=luc.isoformat(), cap_nhat_luc=luc.isoformat(),
            ),
            [MucDon(ma_sach, tieu_de, gia, 1)], ma_thao_tac,
        )


def nap_mau(csdl, duong_dan):
    return NapDuLieuMau(csdl).nap(duong_dan)
