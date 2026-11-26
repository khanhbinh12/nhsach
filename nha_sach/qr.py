"""Tạo SVG cho QR nhận chuyển khoản hoặc cho luồng trình diễn."""
from binascii import crc_hqx
from io import BytesIO
import re

from .mo_hinh import TrangThaiDon, chinh_sach_thanh_toan


def _truong(ma, gia_tri):
    return f"{ma}{len(gia_tri.encode('ascii')):02d}{gia_tri}"


def noi_dung_vietqr(bin_ngan_hang, so_tk, so_tien, noi_dung_ck):
    if not re.fullmatch(r"[0-9]{6}", bin_ngan_hang) or not re.fullmatch(r"[0-9]{1,19}", so_tk):
        raise ValueError("BIN ngân hàng hoặc số tài khoản không hợp lệ.")
    tai_khoan = _truong("00", bin_ngan_hang) + _truong("01", so_tk)
    nguoi_nhan = (
        _truong("00", "A000000727") + _truong("01", tai_khoan) + _truong("02", "QRIBFTTA")
    )
    payload = (
        _truong("00", "01") + _truong("01", "12") + _truong("38", nguoi_nhan)
        + _truong("53", "704") + _truong("54", str(so_tien)) + _truong("58", "VN")
        + _truong("62", _truong("08", noi_dung_ck)) + "6304"
    )
    return payload + f"{crc_hqx(payload.encode('ascii'), 0xffff):04X}"


def thong_tin_qr(don, ngan_hang):
    if (not chinh_sach_thanh_toan(don.phuong_thuc).can_qr() or don.da_thanh_toan
            or don.trang_thai == TrangThaiDon.DA_HUY or not don.tong):
        return None, None
    import segno

    noi_dung_ck = f"NHASACH {don.ma_tra_cuu}"
    if all(ngan_hang.get(ten) for ten in ("bin", "ten", "so_tk", "chu_tk")):
        payload = noi_dung_vietqr(ngan_hang["bin"], ngan_hang["so_tk"], don.tong, noi_dung_ck)
        thong_tin = {ten: ngan_hang[ten] for ten in ("ten", "so_tk", "chu_tk")}
    else:
        payload = f"DEMO - KHONG CHUYEN TIEN - {noi_dung_ck} - {don.tong} VND"
        thong_tin = {
            "ten": "Mô phỏng — không chuyển tiền", "so_tk": "Không có tài khoản thật",
            "chu_tk": "Nhà sách trình diễn",
        }
    tep = BytesIO()
    segno.make_qr(payload, error="m").save(tep, kind="svg", xmldecl=False, svgns=True, scale=4)
    return tep.getvalue().decode("utf-8"), dict(thong_tin, noi_dung_ck=noi_dung_ck)
