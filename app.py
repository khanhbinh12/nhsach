"""Entrypoint chạy nhà sách trên localhost và nạp dữ liệu mẫu lần đầu."""
import os
from pathlib import Path
from secrets import token_urlsafe
from tempfile import NamedTemporaryFile

from nha_sach.web import create_app


def khoa_bi_mat(duong_dan):
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    khoa_ghi = duong_dan.with_name(duong_dan.name + ".lock")
    with khoa_ghi.open("a+b") as tep_khoa:
        if os.name == "nt":
            import msvcrt
            tep_khoa.seek(0)
            msvcrt.locking(tep_khoa.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(tep_khoa, fcntl.LOCK_EX)
        if not duong_dan.exists():
            with NamedTemporaryFile(dir=duong_dan.parent, delete=False, mode="w", encoding="ascii") as tep:
                tam = Path(tep.name)
                tep.write(token_urlsafe(48))
            try:
                os.replace(tam, duong_dan)
            finally:
                tam.unlink(missing_ok=True)
        khoa = duong_dan.read_text(encoding="ascii").strip()
        if not khoa:
            raise RuntimeError("Tệp khóa bí mật đang trống.")
        return khoa


def chay():
    cau_hinh = {"NAP_DU_LIEU_MAU": True}
    for ten, bien in (
        ("NHA_SACH_DB", "NHA_SACH_DB"),
        ("NHA_SACH_MAT_KHAU", "NHA_SACH_MAT_KHAU"),
        ("SECRET_KEY", "NHA_SACH_KHOA"),
    ):
        if gia_tri := os.environ.get(bien):
            cau_hinh[ten] = gia_tri
    if "SECRET_KEY" not in cau_hinh:
        cau_hinh["SECRET_KEY"] = khoa_bi_mat(Path(__file__).resolve().parent / "instance" / "khoa_bi_mat")
    thong_tin = {
        ten: gia_tri for ten in ("ten", "dia_chi", "dien_thoai")
        if (gia_tri := os.environ.get(f"NHA_SACH_{ten.upper()}"))
    }
    if thong_tin:
        cau_hinh["CUA_HANG"] = thong_tin
    cau_hinh["NGAN_HANG"] = {
        ten: os.environ.get(f"NHA_SACH_NGAN_HANG_{ten.upper()}", "")
        for ten in ("bin", "ten", "so_tk", "chu_tk")
    }
    app = create_app(cau_hinh)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)


if __name__ == "__main__":
    chay()
