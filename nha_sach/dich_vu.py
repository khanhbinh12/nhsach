"""Dịch vụ mua hàng và quản lý trạng thái đơn."""
from dataclasses import dataclass
from datetime import date, timedelta
from collections import Counter
from hmac import compare_digest
import re

from werkzeug.security import check_password_hash, generate_password_hash

from .dong_ho import DongHo
from .kho import (
    CoSoDuLieu, KhoBaoCaoDon, KhoDanhGia, KhoDanhMuc, KhoDonHang,
    KhoKhamPha, KhoKhachHang, KhoMaGiamGia, KhoReview, KhoSach, KhoThaoTacSach,
)
from .loi import HetHang, KhongTimThay, LoiNghiepVu, LoiTruong
from .mo_hinh import ChinhSachGiaoHang, MucDon, PhuongThuc, SoDienThoai, TrangThaiDon, TrangThaiReview, chinh_sach_thanh_toan, quy_tac_giam_gia


def so_nguyen(gia_tri, ten):
    try:
        so = int(gia_tri)
    except (TypeError, ValueError) as exc:
        raise LoiNghiepVu(f"{ten} phải là số nguyên.") from exc
    if not 0 <= so <= 10**12:
        raise LoiNghiepVu(f"{ten} nằm ngoài khoảng cho phép.")
    return so


def dien_thoai_hop_le(gia_tri):
    so = SoDienThoai.chuan_hoa(gia_tri)
    if so is None:
        raise LoiTruong(dien_thoai="Nhập số điện thoại Việt Nam gồm 10 chữ số.")
    return so


@dataclass
class MucGio:
    sach: object
    so_luong: int

    @property
    def thanh_tien(self):
        return self.sach.gia * self.so_luong


@dataclass
class XemGio:
    muc: list[MucGio]
    tam_tinh: int
    ma_giam_gia: object
    giam_gia: int
    phi_giao: int
    tong: int
    canh_bao: list[str]
    loi_ma_giam_gia: str | None = None

    @property
    def con_thieu_mien_phi(self):
        return ChinhSachGiaoHang().con_thieu(self.tam_tinh - self.giam_gia)


class DichVu:
    def __init__(self, csdl, dong_ho=None):
        self.csdl = csdl
        self.dong_ho = dong_ho if dong_ho is not None else DongHo()



class DichVuDanhMuc(DichVu):
    def danh_muc(self):
        with self.csdl.doc() as conn:
            return KhoDanhMuc(conn).danh_sach()

    def _ky_doanh_so(self):
        luc = self.dong_ho.bay_gio()
        return (luc - timedelta(days=30)).isoformat(), luc.isoformat()

    def trang_chu(self, ma_vua_xem=()):
        with self.csdl.doc() as conn:
            kho = KhoKhamPha(conn)
            ung_vien = kho.ung_vien_trang_chu(*self._ky_doanh_so())
            danh_muc = KhoDanhMuc(conn).danh_sach_kem_dem_sach()
            vua_xem = kho.theo_ma(ma_vua_xem)
        return dict(
            **self._chia_khoi_trang_chu(ung_vien, {sach.ma for sach in vua_xem}),
            danh_muc=[dict(danh_muc=muc.danh_muc, so_sach=muc.so_sach_dang_ban)
                      for muc in danh_muc if muc.so_sach_dang_ban > 0],
            vua_xem=vua_xem,
        )

    @staticmethod
    def _chia_khoi_trang_chu(ung_vien, da_chon):

        def lay(hang, gioi_han, dieu_kien=None):
            ket_qua = []
            for muc in sorted(ung_vien, key=lambda item: item[hang]):
                ma = muc["sach"].ma
                if ma not in da_chon and (dieu_kien is None or muc[dieu_kien]):
                    da_chon.add(ma)
                    ket_qua.append(muc)
                    if len(ket_qua) == gioi_han:
                        break
            return ket_qua

        def sach(muc):
            return [item["sach"] for item in muc]

        noi_bat = sach(lay("hang_noi_bat", 1))
        ban_chay = lay("hang_ban", 8, "so_ban_that")
        goc_review = [
            dict(sach=muc["sach"], trich=" ".join(re.split(
                r"(?<=[.!?…])\s+", " ".join(muc["noi_dung_review"].split()), maxsplit=2,
            )[:2]))
            for muc in lay("hang_review", 8, "noi_dung_review")
        ]
        sach_moi = sach(lay("hang_moi", 8))
        uu_dai = sach(lay("hang_giam", 8, "ty_le_giam"))
        tieu_diem = sach(lay("hang_noi_bat", 3))
        if len(ban_chay) < 8:
            ten_khoi = "Gợi ý cho bạn"
            ban_chay += lay("hang_noi_bat", 8 - len(ban_chay))
        else:
            ten_khoi = "Bán chạy"
        return dict(noi_bat=noi_bat[0] if noi_bat else None, sach_moi=sach_moi,
                    ban_chay=sach(ban_chay), ten_khoi=ten_khoi, tieu_diem=tieu_diem,
                    uu_dai=uu_dai, goc_review=goc_review)

    def tim_sach(self, **bo_loc):
        with self.csdl.doc() as conn:
            thong_ke = KhoDanhMuc(conn).danh_sach_kem_dem_sach()
            danh_muc = [muc.danh_muc for muc in thong_ke]
            ky = self._ky_doanh_so()
            return dict(
                ket_qua=KhoSach(conn).tim(**bo_loc, ky_doanh_so=ky), bo_loc=bo_loc, danh_muc=danh_muc,
                danh_muc_kem_dem=thong_ke,
                danh_muc_dang_chon=next(
                    (muc for muc in danh_muc if muc.duong_dan == bo_loc.get("danh_muc")), None,
                ),
            )

    def goi_y_sach(self, q):
        with self.csdl.doc() as conn:
            return KhoSach(conn).tim(q=q, moi_trang=6, chi_goi_y=True).muc

    def sach_dang_ban(self, ma):
        with self.csdl.doc() as conn:
            sach = KhoSach(conn).lay(ma)
        if sach is None or not sach.dang_ban:
            raise KhongTimThay("Không tìm thấy sách.")
        return sach

    def chi_tiet_sach(self, ma, ma_vua_xem=()):
        with self.csdl.doc() as conn:
            kho_sach = KhoKhamPha(conn)
            sach = kho_sach.lay(ma, self._ky_doanh_so())
            if sach is None or not sach.dang_ban:
                raise KhongTimThay("Không tìm thấy sách.")
            danh_muc = next(muc for muc in KhoDanhMuc(conn).danh_sach() if muc.ma == sach.ma_danh_muc)
            cung_tac_gia, lien_quan = kho_sach.cung_tac_gia_va_the_loai(sach)
            return dict(
                sach=sach, danh_muc_sach=danh_muc, danh_gia=[vars(item) for item in KhoDanhGia(conn).cua_sach(ma)],
                bai_review=KhoReview(conn).da_duyet_cua_sach(ma),
                cung_tac_gia=cung_tac_gia, lien_quan=lien_quan,
                vua_xem=kho_sach.theo_ma([muc for muc in ma_vua_xem if muc != ma]),
            )


class DichVuTaiKhoan(DichVu):
    def __init__(self, csdl, dong_ho=None):
        super().__init__(csdl, dong_ho)
        self._mat_khau_gia = generate_password_hash("tai-khoan-khong-ton-tai")

    def lay_khach(self, ma):
        if ma is None:
            return None
        with self.csdl.doc() as conn:
            return KhoKhachHang(conn).lay(ma)

    def dang_ky(self, ho_ten, email, dien_thoai, mat_khau, mat_khau_lai):
        ho_ten, email = ho_ten.strip(), email.strip().lower()
        if not ho_ten:
            raise LoiTruong(ho_ten="Hãy nhập họ tên.")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise LoiTruong(email="Hãy nhập địa chỉ email hợp lệ.")
        dien_thoai = dien_thoai_hop_le(dien_thoai)
        if not 8 <= len(mat_khau) <= 256:
            raise LoiTruong(mat_khau="Mật khẩu phải dài từ 8 đến 256 ký tự.")
        if mat_khau != mat_khau_lai:
            raise LoiTruong(mat_khau_lai="Mật khẩu nhập lại không khớp.")
        mat_khau_bam = generate_password_hash(mat_khau)
        with self.csdl.giao_dich() as conn:
            kho = KhoKhachHang(conn)
            if kho.theo_email(email):
                raise LoiTruong(email="Email đã được đăng ký.")
            return kho.them(ho_ten, email, dien_thoai, mat_khau_bam, self.dong_ho.bay_gio())

    def dang_nhap(self, email, mat_khau):
        if len(mat_khau) > 256:
            return None
        with self.csdl.doc() as conn:
            khach = KhoKhachHang(conn).theo_email(email.strip().lower())
        mat_khau_bam = khach.mat_khau_bam if khach else self._mat_khau_gia
        if check_password_hash(mat_khau_bam, mat_khau):
            return khach
        return None

    def cap_nhat_ho_so(self, ma, ho_ten, dien_thoai, dia_chi):
        ho_ten, dia_chi = ho_ten.strip(), dia_chi.strip()
        loi = {}
        if not ho_ten:
            loi["ho_ten"] = "Hãy nhập họ tên."
        dien_thoai = SoDienThoai.chuan_hoa(dien_thoai)
        if not dien_thoai:
            loi["dien_thoai"] = "Số điện thoại phải là số Việt Nam hợp lệ."
        if loi:
            raise LoiTruong(**loi)
        with self.csdl.giao_dich() as conn:
            KhoKhachHang(conn).cap_nhat_ho_so(ma, ho_ten, dien_thoai, dia_chi)

    def don_cua_khach(self, ma):
        with self.csdl.doc() as conn:
            return KhoDonHang(conn).cua_khach(ma)


class DichVuDanhGia(DichVu):
    def thong_tin_danh_gia(self, ma_sach, ma_khach):
        if ma_khach is None:
            return False, None
        with self.csdl.doc() as conn:
            kho = KhoDanhGia(conn)
            return kho.da_mua(ma_sach, ma_khach), kho.cua_khach(ma_sach, ma_khach)

    def luu_danh_gia(self, ma_sach, ma_khach, so_sao, noi_dung):
        noi_dung = noi_dung.strip()
        if so_sao not in range(1, 6) or not 1 <= len(noi_dung) <= 2000:
            raise LoiNghiepVu("Hãy chọn từ 1 đến 5 sao và nhập nội dung đánh giá.")
        with self.csdl.giao_dich() as conn:
            kho = KhoDanhGia(conn)
            if not kho.da_mua(ma_sach, ma_khach):
                raise LoiNghiepVu("Bạn cần mua sách trước khi đánh giá.")
            kho.luu(ma_sach, ma_khach, so_sao, noi_dung, self.dong_ho.bay_gio())


class DichVuDatHang(DichVu):
    def _tinh_gio(self, conn, gio, ma_giam_gia, *, dat_hang=False):
        sach_theo_ma = {sach.ma: sach for sach in KhoKhamPha(conn).theo_ma(gio, dang_ban=False)}
        muc, canh_bao = [], []
        for ma, so_luong in gio.items():
            if type(so_luong) is not int or so_luong < 1:
                raise LoiNghiepVu("Số lượng phải là số nguyên dương.")
            sach = sach_theo_ma.get(ma)
            if sach is None or not sach.dang_ban or so_luong > sach.ton_kho:
                loi = f"{sach.tieu_de if sach else 'Một sách trong giỏ'} không còn đủ hàng."
                if dat_hang:
                    raise HetHang(loi)
                canh_bao.append(loi)
            if sach is not None and sach.dang_ban:
                muc.append(MucGio(sach, so_luong))

        tam_tinh = sum(item.thanh_tien for item in muc)
        ma_giam_gia = (ma_giam_gia or "").strip().upper()
        giam_gia = 0
        ma = loi_ma = None
        if ma_giam_gia:
            ma = KhoMaGiamGia(conn).lay(ma_giam_gia)
            hom_nay = self.dong_ho.hom_nay()
            loi_ma = ma.ly_do(tam_tinh, hom_nay) if ma else f"Mã {ma_giam_gia} không tồn tại."
            if loi_ma:
                if dat_hang:
                    raise LoiTruong(ma_giam_gia=loi_ma)
                canh_bao.append(loi_ma)
                ma = None
            else:
                giam_gia = ma.tinh_giam(tam_tinh, hom_nay)
        sau_giam = tam_tinh - giam_gia
        phi_giao = ChinhSachGiaoHang().tinh_phi(sau_giam, bool(muc))
        return XemGio(muc, tam_tinh, ma, giam_gia, phi_giao, sau_giam + phi_giao, canh_bao, loi_ma)

    def xem_gio(self, gio, ma_giam_gia=None):
        with self.csdl.doc() as conn:
            return self._tinh_gio(conn, gio, ma_giam_gia)

    def dat_hang(self, gio, thong_tin, ma_thao_tac, ma_giam_gia=None, ma_khach=None):
        if not re.fullmatch(r"[\w-]{22,128}", ma_thao_tac or "", flags=re.ASCII):
            raise LoiNghiepVu("Hãy mở lại trang đặt hàng.")
        with self.csdl.giao_dich() as conn:
            kho_don = KhoDonHang(conn)
            don_cu = kho_don.lay_theo_thao_tac(ma_thao_tac)
            if don_cu:
                return don_cu
            if not gio:
                raise LoiNghiepVu("Giỏ hàng đang trống.")
            ho_ten = thong_tin.get("ho_ten", "").strip()
            dia_chi = thong_tin.get("dia_chi", "").strip()
            if not ho_ten:
                raise LoiTruong(ho_ten="Hãy nhập họ tên người nhận.")
            dien_thoai = dien_thoai_hop_le(thong_tin.get("dien_thoai", ""))
            if not dia_chi:
                raise LoiTruong(dia_chi="Hãy nhập địa chỉ giao hàng.")
            try:
                phuong_thuc = PhuongThuc(thong_tin.get("phuong_thuc"))
            except ValueError as exc:
                raise LoiTruong(phuong_thuc="Hãy chọn phương thức thanh toán.") from exc
            xem = self._tinh_gio(conn, gio, ma_giam_gia, dat_hang=True)
            kho_sach = KhoSach(conn)
            for item in xem.muc:
                if not kho_sach.tru_ton(item.sach.ma, item.so_luong):
                    raise HetHang(f"{item.sach.tieu_de} không còn đủ hàng.")
            ma = xem.ma_giam_gia.ma if xem.ma_giam_gia else None
            if ma and not KhoMaGiamGia(conn).doi_luot(ma, 1):
                raise LoiNghiepVu("Mã giảm giá đã hết lượt.")
            ma_tra_cuu = kho_don.tao_ma_tra_cuu()
            luc = self.dong_ho.bay_gio()
            du_lieu = dict(
                ma_tra_cuu=ma_tra_cuu, ma_khach=ma_khach, ho_ten=ho_ten,
                dien_thoai=dien_thoai, dia_chi=dia_chi,
                ghi_chu=thong_tin.get("ghi_chu", "").strip(), phuong_thuc=phuong_thuc,
                trang_thai=TrangThaiDon.CHO_XAC_NHAN, tam_tinh=xem.tam_tinh,
                giam_gia=xem.giam_gia, phi_giao=xem.phi_giao, tong=xem.tong,
                ma_giam_gia=ma, tao_luc=luc.isoformat(), cap_nhat_luc=luc.isoformat(),
            )
            muc = [MucDon(m.sach.ma, m.sach.tieu_de, m.sach.gia, m.so_luong) for m in xem.muc]
            don = kho_don.them(du_lieu, muc, ma_thao_tac)
            if ma_khach is not None:
                KhoKhachHang(conn).cap_nhat_dia_chi(ma_khach, dia_chi)
            return don

    def lay_don(self, ma_tra_cuu):
        with self.csdl.doc() as conn:
            don = KhoDonHang(conn).lay_theo_ma_tra_cuu(ma_tra_cuu.strip().upper())
        if don is None:
            raise KhongTimThay("Không tìm thấy đơn hàng.")
        return don

    def tra_cuu(self, ma_tra_cuu, dien_thoai):
        try:
            don = self.lay_don(ma_tra_cuu)
        except KhongTimThay:
            return None
        dien_thoai = SoDienThoai.chuan_hoa(dien_thoai)
        dien_thoai_don = SoDienThoai.chuan_hoa(don.dien_thoai)
        if dien_thoai and dien_thoai_don and compare_digest(dien_thoai, dien_thoai_don):
            return don
        return None


class DichVuDonHang(DichVu):
    def doi_trang_thai(self, ma, trang_thai, *, da_hoan_tien=False, khach_huy=False):
        with self.csdl.giao_dich() as conn:
            kho_don = KhoDonHang(conn)
            don = kho_don.lay(ma)
            if don is None:
                raise KhongTimThay("Không tìm thấy đơn hàng.")
            moi = don.chuyen_sang(trang_thai, da_hoan_tien=da_hoan_tien, khach_huy=khach_huy)
            if moi.trang_thai == TrangThaiDon.DA_HUY:
                kho_sach = KhoSach(conn)
                for item in don.muc:
                    if not kho_sach.doi_ton(item.ma_sach, item.so_luong):
                        raise LoiNghiepVu("Không trả lại được tồn kho.")
                if don.ma_giam_gia and not KhoMaGiamGia(conn).doi_luot(don.ma_giam_gia, -1):
                    raise LoiNghiepVu("Không trả lại được lượt mã giảm giá.")
            return kho_don.doi_trang_thai(
                ma, moi.trang_thai, moi.da_hoan_tien, moi.da_thanh_toan, self.dong_ho.bay_gio(),
            )

    def xac_nhan_thanh_toan(self, ma):
        with self.csdl.giao_dich() as conn:
            kho_don = KhoDonHang(conn)
            don = kho_don.lay(ma)
            if don is None:
                raise KhongTimThay("Không tìm thấy đơn hàng.")
            if don.trang_thai == TrangThaiDon.DA_HUY or not chinh_sach_thanh_toan(don.phuong_thuc).can_qr():
                raise LoiNghiepVu("Đơn này không thể xác nhận chuyển khoản.")
            if don.da_thanh_toan:
                return don
            return kho_don.xac_nhan_thanh_toan(ma, self.dong_ho.bay_gio())

    def lay_don(self, ma):
        with self.csdl.doc() as conn:
            don = KhoDonHang(conn).lay(ma)
        if don is None:
            raise KhongTimThay("Không tìm thấy đơn hàng.")
        return don

    def danh_sach_don(self, trang_thai, trang, q=""):
        try:
            loc = TrangThaiDon(trang_thai) if trang_thai else None
        except ValueError as exc:
            raise LoiNghiepVu("Trạng thái đơn không hợp lệ.") from exc
        with self.csdl.doc() as conn:
            ket_qua = KhoDonHang(conn).danh_sach(loc, trang, q=q, dien_thoai=SoDienThoai.chuan_hoa(q))
        return dict(ket_qua=ket_qua, loc=loc, cac_trang_thai=list(TrangThaiDon), q=q)


class DichVuSach(DichVu):
    def danh_sach_sach(self, loc="", **bo_loc):
        loc = loc if loc in {"sap_het", "ngung_ban"} else ""
        with self.csdl.doc() as conn:
            return dict(ket_qua=KhoSach(conn).tim(**bo_loc, dang_ban=False, loc=loc),
                        danh_muc=KhoDanhMuc(conn).danh_sach(), bo_loc=dict(bo_loc, loc=loc), loc=loc)

    def lay_sach(self, ma):
        with self.csdl.doc() as conn:
            sach = KhoSach(conn).lay(ma)
        if sach is None:
            raise KhongTimThay("Không tìm thấy sách.")
        return sach

    def luu_sach(self, form, ma=None, anh_bia=None):
        def chu(ten):
            return form.get(ten, "").strip()

        du_lieu = {ten: chu(ten) for ten in ("tieu_de", "tac_gia", "mo_ta", "mau_bia")}
        if not du_lieu["tieu_de"] or not du_lieu["tac_gia"]:
            loi = {}
            if not du_lieu["tieu_de"]:
                loi["tieu_de"] = "Hãy nhập tên sách."
            if not du_lieu["tac_gia"]:
                loi["tac_gia"] = "Hãy nhập tên tác giả."
            raise LoiTruong(**loi)
        du_lieu["mau_bia"] = du_lieu["mau_bia"] or "#334455"
        if not re.fullmatch(r"#[a-fA-F0-9]{6}", du_lieu["mau_bia"]):
            raise LoiTruong(mau_bia="Màu bìa phải có dạng #rrggbb.")
        bat_buoc = {"gia": "Giá bán", "gia_bia": "Giá bìa", "ton_kho": "Tồn kho", "ma_danh_muc": "Danh mục"}
        tuy_chon = {"nam_xuat_ban": "Năm xuất bản", "so_trang": "Số trang"}
        loi = {}
        for ten, nhan in (bat_buoc | tuy_chon).items():
            try:
                du_lieu[ten] = None if ten in tuy_chon and not chu(ten) else so_nguyen(chu(ten), nhan)
            except LoiNghiepVu as exc:
                loi[ten] = str(exc)
        if loi:
            raise LoiTruong(**loi)
        if du_lieu["gia_bia"] < du_lieu["gia"]:
            raise LoiTruong(gia_bia="Giá bìa không được thấp hơn giá bán.")
        du_lieu["nha_xuat_ban"] = chu("nha_xuat_ban") or None
        du_lieu["dang_ban"] = any(v in ("1", "on", "true") for v in form.getlist("dang_ban"))
        du_lieu["ngay_them"] = self.dong_ho.bay_gio().isoformat()
        with self.csdl.giao_dich() as conn:
            kho = KhoSach(conn)
            if du_lieu["ma_danh_muc"] not in {muc.ma for muc in KhoDanhMuc(conn).danh_sach()}:
                raise LoiTruong(ma_danh_muc="Danh mục không tồn tại.")
            cu = kho.lay(ma) if ma is not None else None
            if ma is not None and cu is None:
                raise KhongTimThay("Không tìm thấy sách.")
            du_lieu["anh_bia"] = anh_bia or (cu.anh_bia if cu else None)
            ma_thao_tac = chu("ma_thao_tac")
            if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", ma_thao_tac):
                raise LoiNghiepVu("Hãy mở lại biểu mẫu sách.")
            if not cu:
                ma_cu = KhoThaoTacSach(conn).ma_sach_theo_thao_tac_them(ma_thao_tac)
                if ma_cu is not None:
                    return kho.lay(ma_cu), False
            if cu:
                if not KhoThaoTacSach(conn).ghi_nhan_sua(ma, ma_thao_tac):
                    return cu, False
                chenh = du_lieu["ton_kho"] - so_nguyen(chu("ton_kho_goc"), "tồn kho gốc")
                if chenh and not kho.doi_ton(ma, chenh):
                    raise LoiTruong(ton_kho="Tồn kho hiện tại không đủ để giảm số lượng đã nhập.")
            ma_da_luu = kho.luu(du_lieu, ma)
            if ma is None:
                KhoThaoTacSach(conn).ghi_nhan_them(ma_thao_tac, ma_da_luu)
            return kho.lay(ma_da_luu), True

    def xoa_sach(self, ma):
        return self.doi_trang_thai_ban(ma, False)

    def doi_trang_thai_ban(self, ma, dang_ban):
        with self.csdl.giao_dich() as conn:
            if not KhoSach(conn).doi_trang_thai_ban(ma, dang_ban):
                raise KhongTimThay("Không tìm thấy sách.")

    def danh_muc(self):
        with self.csdl.doc() as conn:
            return [vars(muc) for muc in KhoDanhMuc(conn).danh_sach_kem_dem_sach()]

    def luu_danh_muc(self, ten, duong_dan, thu_tu, ma=None):
        ten, duong_dan = ten.strip(), duong_dan.strip().lower()
        if not ten or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", duong_dan):
            raise LoiNghiepVu("Hãy nhập tên và slug danh mục không dấu.")
        with self.csdl.giao_dich() as conn:
            kho = KhoDanhMuc(conn)
            thu_tu = so_nguyen(thu_tu, "thứ tự")
            if ma is None:
                if not kho.them(ten, duong_dan, thu_tu):
                    raise LoiNghiepVu("Slug danh mục đã tồn tại.")
            elif not kho.sua(so_nguyen(ma, "mã danh mục"), ten, duong_dan, thu_tu):
                raise LoiNghiepVu("Danh mục không tồn tại hoặc slug đã được dùng.")

    def xoa_danh_muc(self, ma):
        with self.csdl.giao_dich() as conn:
            if not KhoDanhMuc(conn).xoa(ma):
                raise LoiNghiepVu("Danh mục không tồn tại hoặc vẫn còn sách.")


class DichVuMaGiamGia(DichVu):
    def danh_sach_ma_giam_gia(self):
        with self.csdl.doc() as conn:
            return KhoMaGiamGia(conn).danh_sach()

    def them_ma_giam_gia(self, form):
        ma, kieu = form.get("ma", "").strip().upper(), form.get("kieu")
        if not re.fullmatch(r"[A-Z0-9_-]{1,32}", ma):
            raise LoiNghiepVu("Mã hoặc kiểu giảm giá không hợp lệ.")
        try:
            quy_tac = quy_tac_giam_gia(kieu)
        except ValueError as exc:
            raise LoiNghiepVu("Mã hoặc kiểu giảm giá không hợp lệ.") from exc
        gia_tri = so_nguyen(form.get("gia_tri"), "giá trị giảm")
        if not quy_tac.gia_tri_hop_le(gia_tri):
            raise LoiNghiepVu("Giá trị giảm không hợp lệ.")
        het_han = form.get("het_han", "").strip()
        try:
            het_han = date.fromisoformat(het_han) if het_han else None
        except ValueError as exc:
            raise LoiNghiepVu("Ngày hết hạn không hợp lệ.") from exc
        luot = form.get("so_luot_toi_da", "").strip()
        du_lieu = dict(
            ma=ma, kieu=kieu, gia_tri=gia_tri, het_han=het_han.isoformat() if het_han else None,
            don_toi_thieu=so_nguyen(form.get("don_toi_thieu", "0"), "đơn tối thiểu"),
            so_luot_toi_da=so_nguyen(luot, "số lượt") if luot else None,
        )
        with self.csdl.giao_dich() as conn:
            if not KhoMaGiamGia(conn).them(du_lieu):
                raise LoiNghiepVu("Mã giảm giá đã tồn tại.")

    def bat_tat_ma(self, ma):
        with self.csdl.giao_dich() as conn:
            if not KhoMaGiamGia(conn).bat_tat(ma):
                raise KhongTimThay("Không tìm thấy mã giảm giá.")


class DichVuKhachVaDanhGia(DichVu):
    def danh_sach_khach(self):
        with self.csdl.doc() as conn:
            return [vars(item) for item in KhoKhachHang(conn).danh_sach()]

    def danh_sach_danh_gia(self):
        with self.csdl.doc() as conn:
            return [vars(item) for item in KhoDanhGia(conn).danh_sach()]

    def doi_an_danh_gia(self, ma):
        with self.csdl.giao_dich() as conn:
            if not KhoDanhGia(conn).doi_an(ma):
                raise KhongTimThay("Không tìm thấy đánh giá.")


class DichVuBaoCao(DichVu):
    def xuat_don(self):
        with self.csdl.doc() as conn:
            return KhoBaoCaoDon(conn).xuat_don()

    def tong_quan(self):
        hom_nay = self.dong_ho.hom_nay()
        nam, thang = divmod(hom_nay.year * 12 + hom_nay.month - 12, 12)
        doanh_thu = self.doanh_thu(date(nam, thang + 1, 1))
        theo_ngay = [hom_nay - timedelta(days=i) for i in reversed(range(30))]
        thang_hien_tai = hom_nay.year * 12 + hom_nay.month - 1
        theo_thang = [divmod(thang_hien_tai - i, 12) for i in reversed(range(12))]
        thang = self.gop_doanh_thu_thang(doanh_thu)
        with self.csdl.doc() as conn:
            kho = KhoSach(conn)
            sap_het = kho.sap_het()
            ban_chay = kho.tim(sap_xep="ban_chay", moi_trang=10, dang_ban=False).muc
            cho_xac_nhan = KhoBaoCaoDon(conn).dem_cho_xac_nhan()
            so_khach = KhoKhachHang(conn).dem()
        return dict(
            the=dict(
                doanh_thu_thang=thang[hom_nay.isoformat()[:7]],
                don_cho_xac_nhan=cho_xac_nhan, sach_sap_het=len(sap_het), so_khach=so_khach,
            ),
            doanh_thu_ngay=[dict(ngay=ngay.isoformat(), tien=doanh_thu.get(ngay, 0)) for ngay in theo_ngay],
            doanh_thu_thang=[dict(thang=f"{nam:04d}-{t + 1:02d}", tien=thang[f"{nam:04d}-{t + 1:02d}"]) for nam, t in theo_thang],
            ban_chay=[dict(sach=sach, so_ban=sach.da_ban) for sach in ban_chay if sach.da_ban],
            sap_het=sap_het,
        )

    @staticmethod
    def gop_doanh_thu_thang(doanh_thu):
        thang = Counter()
        for ngay, tien in doanh_thu.items():
            thang[ngay.isoformat()[:7]] += tien
        return thang

    def doanh_thu(self, tu_ngay=None):
        with self.csdl.doc() as conn:
            return {item.ngay: item.tien for item in KhoBaoCaoDon(conn).doanh_thu(tu_ngay)}


class DichVuReview(DichVu):
    @staticmethod
    def _du_lieu(tieu_de, noi_dung, tac_gia_review):
        gia_tri = tuple(chu.strip() for chu in (tieu_de, noi_dung, tac_gia_review))
        loi = {}
        quy_tac = (
            ("tieu_de", "Tiêu đề", 200),
            ("noi_dung", "Nội dung", 20000),
            ("tac_gia_review", "Tên tác giả bài review", 120),
        )
        for (truong, ten, toi_da), chu in zip(quy_tac, gia_tri):
            if not chu:
                loi[truong] = f"{ten} không được để trống."
            elif len(chu) > toi_da:
                loi[truong] = f"{ten} tối đa {toi_da} ký tự."
        if loi:
            raise LoiTruong(**loi)
        return gia_tri

    def sach_chua_co_review(self):
        with self.csdl.doc() as conn:
            return KhoReview(conn).sach_chua_co_review()

    def tao_nhap_review(self, ma_sach, tieu_de, noi_dung, tac_gia_review):
        du_lieu = self._du_lieu(tieu_de, noi_dung, tac_gia_review)
        with self.csdl.giao_dich() as conn:
            if KhoSach(conn).lay(ma_sach) is None:
                raise KhongTimThay("Không tìm thấy sách.")
            bai = KhoReview(conn).tao_nhap(ma_sach, *du_lieu, self.dong_ho.bay_gio())
            if bai is None:
                raise LoiNghiepVu("Sách này đã có bài review. Hãy sửa bài đã có.")
            return bai

    def nhap_review(self, danh_sach):
        ket_qua = []
        luc = self.dong_ho.bay_gio()
        with self.csdl.giao_dich() as conn:
            kho_sach, kho_review = KhoSach(conn), KhoReview(conn)
            for item in danh_sach:
                du_lieu = self._du_lieu(item["tieu_de"], item["noi_dung"], item["tac_gia_review"])
                ma = item.get("ma_sach")
                if ma is None:
                    cac_ma = kho_sach.ma_theo_tieu_de(item.get("tieu_de_sach", ""))
                    if len(cac_ma) != 1:
                        raise LoiNghiepVu("Tên sách không khớp duy nhất. Hãy dùng mã sách.")
                    ma = cac_ma[0]
                elif kho_sach.lay(ma) is None:
                    raise KhongTimThay("Không tìm thấy sách.")
                bai = kho_review.tao_nhap(ma, *du_lieu, luc)
                if bai is None:
                    raise LoiNghiepVu(f"Sách mã {ma} đã có review; không ghi đè.")
                ket_qua.append(bai)
        return ket_qua

    def xem_review(self, ma):
        with self.csdl.doc() as conn:
            bai = KhoReview(conn).lay(ma)
        if bai is None:
            raise KhongTimThay("Không tìm thấy bài review.")
        return bai

    def danh_sach_review(self, trang_thai=""):
        try:
            loc = TrangThaiReview(trang_thai) if trang_thai else None
        except ValueError as exc:
            raise LoiNghiepVu("Trạng thái review không hợp lệ.") from exc
        with self.csdl.doc() as conn:
            return KhoReview(conn).danh_sach(loc)

    def sua_review(self, ma, tieu_de, noi_dung, tac_gia_review):
        du_lieu = self._du_lieu(tieu_de, noi_dung, tac_gia_review)
        with self.csdl.giao_dich() as conn:
            bai = KhoReview(conn).sua(ma, *du_lieu)
            if bai is None:
                raise KhongTimThay("Không tìm thấy bài review.")
            return bai

    def doi_duyet_review(self, ma, duyet):
        trang_thai = TrangThaiReview.DA_DUYET if duyet else TrangThaiReview.NHAP
        luc = self.dong_ho.bay_gio() if duyet else None
        with self.csdl.giao_dich() as conn:
            kho = KhoReview(conn)
            bai = kho.lay(ma)
            if bai is None:
                raise KhongTimThay("Không tìm thấy bài review.")
            if bai.trang_thai == trang_thai:
                return bai
            return kho.doi_trang_thai(ma, trang_thai, luc)


class _NhomDichVu(DichVu):
    def __init__(self, csdl, dong_ho=None):
        super().__init__(csdl, dong_ho)
        self._dich_vu = tuple(lop(csdl, self.dong_ho) for lop in self._lop)

    def __getattr__(self, ten):
        if not ten.startswith("_"):
            for dich_vu in self._dich_vu:
                thao_tac = getattr(dich_vu, ten, None)
                if thao_tac is not None:
                    return thao_tac
        raise AttributeError(ten)


class DichVuCuaHang(_NhomDichVu):
    _lop = (DichVuDanhMuc, DichVuTaiKhoan, DichVuDanhGia, DichVuDatHang)


class DichVuQuanLy(_NhomDichVu):
    _lop = (DichVuDonHang, DichVuSach, DichVuMaGiamGia, DichVuKhachVaDanhGia, DichVuBaoCao, DichVuReview)


def tao_dich_vu(duong_dan, dong_ho=None):
    csdl = CoSoDuLieu(duong_dan)
    csdl.tao_bang()
    return DichVuCuaHang(csdl, dong_ho), DichVuQuanLy(csdl, dong_ho)
