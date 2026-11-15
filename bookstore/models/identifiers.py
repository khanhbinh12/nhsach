"""Sinh mã định danh ngẫu nhiên, đảm bảo không trùng.

Trước đây mỗi model tự bốc 6 ký tự ngẫu nhiên mà không kiểm tra trùng, nên khi kho có khoảng
2.000 sách đã có lúc trùng mã và admin bị báo lỗi "Mã sách đã tồn tại" dù không nhập mã.
Nay các lớp dịch vụ dùng ``IdGenerator.new_id(prefix, taken)``: sinh lại cho tới khi được mã chưa dùng.
"""

from __future__ import annotations

import secrets
from typing import Callable

from ..exceptions import BookstoreError


def _never_taken(_candidate: str) -> bool:
    return False


class IdGenerator:
    """Sinh mã dạng ``TIỀN_TỐ-XXXXXXXX``.

    Bảng chữ bỏ các ký tự dễ nhầm (0/O, 1/I/L) để khách đọc mã đơn qua điện thoại không bị sai.
    Với 8 ký tự có ~1,1 nghìn tỷ tổ hợp – gần như không bao giờ phải sinh lại.
    """

    ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    MAX_ATTEMPTS = 50

    def __init__(self, length: int = 8, random_part: Callable[[int], str] | None = None) -> None:
        if length < 4:
            raise ValueError("Độ dài phần ngẫu nhiên tối thiểu là 4")
        self._length = length
        self._random_part = random_part or self._secure_random

    def _secure_random(self, length: int) -> str:
        return "".join(secrets.choice(self.ALPHABET) for _ in range(length))

    def new_id(self, prefix: str, taken: Callable[[str], bool] = _never_taken) -> str:
        """Sinh mã chưa có trong hệ thống; ``taken(mã)`` trả về True nếu mã đã được dùng."""
        for _ in range(self.MAX_ATTEMPTS):
            candidate = f"{prefix}-{self._random_part(self._length)}"
            if not taken(candidate):
                return candidate
        raise BookstoreError(f"Không sinh được mã mới cho '{prefix}' sau {self.MAX_ATTEMPTS} lần thử")


DEFAULT_IDS = IdGenerator()
