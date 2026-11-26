"""Xuất CSV UTF-8 có BOM để Excel đọc đúng tiếng Việt."""
import csv
from io import StringIO
import re


def tao_csv(cot, dong):
    tep = StringIO(newline="")
    ghi = csv.writer(tep)
    ghi.writerow(cot)
    ghi.writerows([_o(an) for an in hang] for hang in dong)
    return tep.getvalue().encode("utf-8-sig")


class DienThoaiExcel(str):
    """Biểu diễn số điện thoại bằng chuỗi khi mở CSV bằng Excel."""


def dong_don(dong):
    return (
        dong.ma_tra_cuu, dong.ho_ten, DienThoaiExcel(dong.dien_thoai), dong.dia_chi,
        dong.trang_thai.nhan, dong.phuong_thuc.nhan, dong.tam_tinh, dong.giam_gia,
        dong.phi_giao, dong.tong, dong.tao_luc.strftime("%d/%m/%Y %H:%M"),
    )


def _o(gia_tri):
    if isinstance(gia_tri, DienThoaiExcel) and re.fullmatch(r"[0-9]{8,15}", gia_tri):
        return f'="{gia_tri}"'
    if isinstance(gia_tri, str) and gia_tri.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + gia_tri
    if isinstance(gia_tri, str) and gia_tri.startswith(("\t", "\r", "\n")):
        return "'" + gia_tri
    return gia_tri
