"""Tiện ích dùng chung cho các bài kiểm thử."""

import io
from datetime import datetime, timedelta

from PIL import Image


def make_image(fmt: str = "PNG", size: tuple[int, int] = (900, 1200), color: str = "#b45309") -> bytes:
    """Ảnh thật (Pillow tạo) để kiểm thử upload ảnh bìa."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, fmt)
    return buffer.getvalue()


class FakeClock:
    """Đồng hồ giả để kiểm thử các logic phụ thuộc thời gian (hạn hội viên, thời lượng quảng cáo)."""

    def __init__(self, start: datetime = datetime(2026, 1, 1, 9, 0, 0)) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)
