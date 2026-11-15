"""Theo dõi thay đổi của đối tượng – nền tảng cho Unit of Work.

Mỗi lần một thuộc tính bị gán lại (kể cả qua setter của ``@property``), đối tượng tự đánh dấu
mình là "bẩn" (đã thay đổi). Khi lưu, chỉ các đối tượng bẩn mới phải chuyển sang dict và ghi xuống
CSDL – thay vì chuyển toàn bộ hàng nghìn sách / đơn hàng như trước.
"""

from __future__ import annotations

from typing import Any


class Trackable:
    """Mixin: tự đánh dấu đã thay đổi khi bị gán thuộc tính.

    Đối tượng mới tạo luôn "bẩn" (vì ``__init__`` gán thuộc tính) nên chắc chắn được lưu lần đầu.
    """

    _DIRTY_FLAG = "_tracking_dirty"

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        if name != Trackable._DIRTY_FLAG:
            object.__setattr__(self, Trackable._DIRTY_FLAG, True)

    @property
    def is_dirty(self) -> bool:
        return self.__dict__.get(Trackable._DIRTY_FLAG, True)

    def mark_clean(self) -> None:
        """Gọi sau khi đã lưu thành công."""
        object.__setattr__(self, Trackable._DIRTY_FLAG, False)
