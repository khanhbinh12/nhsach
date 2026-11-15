"""Phân trang dùng chung cho mọi danh sách (sách, đơn hàng, khách hàng…).

Trước khi phân trang, với ~2.000 sách và ~3.000 đơn: trang chủ nặng 1,5 MB, trang đơn hàng
quản trị nặng 4,1 MB vì in ra toàn bộ danh sách.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Generic, Sequence, TypeVar

from flask import request, url_for

T = TypeVar("T")
PAGE_ARG = "trang"


@dataclass(frozen=True)
class Page(Generic[T]):
    """Một trang kết quả."""

    items: Sequence[T]
    number: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        return max(1, ceil(self.total / self.per_page))

    @property
    def has_prev(self) -> bool:
        return self.number > 1

    @property
    def has_next(self) -> bool:
        return self.number < self.pages

    @property
    def first_index(self) -> int:
        return 0 if self.total == 0 else (self.number - 1) * self.per_page + 1

    @property
    def last_index(self) -> int:
        return min(self.number * self.per_page, self.total)

    def window(self, radius: int = 2) -> list[int | None]:
        """Các số trang cần hiện; ``None`` là dấu '…'. Ví dụ: [1, None, 5, 6, 7, 8, 9, None, 40]."""
        shown = {1, self.pages, *range(max(1, self.number - radius), min(self.pages, self.number + radius) + 1)}
        result: list[int | None] = []
        previous = 0
        for number in sorted(shown):
            if number - previous > 1:
                result.append(None)
            result.append(number)
            previous = number
        return result


class Paginator:
    """Cắt một danh sách thành từng trang; số trang sai hoặc vượt quá được tự chỉnh về trang hợp lệ."""

    def __init__(self, per_page: int) -> None:
        if per_page < 1:
            raise ValueError("Số mục mỗi trang phải lớn hơn 0")
        self._per_page = per_page

    def page(self, items: Sequence[T], number: int | str | None) -> Page[T]:
        total = len(items)
        pages = max(1, ceil(total / self._per_page))
        try:
            wanted = int(number or 1)
        except (TypeError, ValueError):
            wanted = 1
        current = min(max(wanted, 1), pages)
        start = (current - 1) * self._per_page
        return Page(items[start:start + self._per_page], current, self._per_page, total)


def paginate(items: Sequence[T], per_page: int) -> Page[T]:
    """Phân trang theo tham số ``?trang=`` của request hiện tại."""
    return Paginator(per_page).page(items, request.args.get(PAGE_ARG))


def page_url(number: int) -> str:
    """Đường dẫn tới trang ``number``, giữ nguyên các bộ lọc đang chọn (tìm kiếm, thể loại…)."""
    args = request.args.to_dict()
    if number > 1:
        args[PAGE_ARG] = str(number)
    else:
        args.pop(PAGE_ARG, None)
    return url_for(request.endpoint, **(request.view_args or {}), **args)
