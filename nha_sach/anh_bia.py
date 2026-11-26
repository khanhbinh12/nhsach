"""Lưu ảnh bìa với tên do ứng dụng tạo."""
from pathlib import Path
from secrets import token_hex

from .loi import LoiNghiepVu


GIOI_HAN = 5 * 1024 * 1024


def luu_anh_bia(tep, thu_muc):
    if tep is None or not tep.filename:
        return None
    noi_dung = tep.stream.read(GIOI_HAN + 1)
    if len(noi_dung) > GIOI_HAN:
        raise LoiNghiepVu("Ảnh bìa tối đa 5 MB.")
    if noi_dung.startswith(b"\x89PNG\r\n\x1a\n"):
        duoi = ".png"
    elif noi_dung.startswith(b"\xff\xd8\xff"):
        duoi = ".jpg"
    elif noi_dung.startswith(b"RIFF") and noi_dung[8:12] == b"WEBP":
        duoi = ".webp"
    else:
        raise LoiNghiepVu("Hãy tải ảnh PNG, JPEG hoặc WebP.")
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    duong_dan = thu_muc / (token_hex(16) + duoi)
    try:
        with duong_dan.open("xb") as file:
            file.write(noi_dung)
    except FileExistsError:
        raise
    except OSError:
        duong_dan.unlink(missing_ok=True)
        raise
    return duong_dan
