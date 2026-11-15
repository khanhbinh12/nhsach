"""Xử lý chuỗi tiếng Việt."""

from __future__ import annotations

import re
import unicodedata


def slugify(text: str, max_length: int = 80, fallback: str = "sach") -> str:
    """Chuyển tiêu đề tiếng Việt thành đường dẫn thân thiện.

    >>> slugify("Lập Trình Hướng Đối Tượng Python")
    'lap-trinh-huong-doi-tuong-python'
    """
    text = (text or "").replace("đ", "d").replace("Đ", "D")  # 'đ' không tách dấu được bằng NFKD
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or fallback
