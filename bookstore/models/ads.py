"""Quảng cáo ủng hộ web (mô phỏng).

Xem quảng cáo KHÔNG mở khóa gì – chỉ là một cách ủng hộ chi phí duy trì web.
Hệ thống ghi nhận lượt xem hợp lệ (xem đủ thời lượng) và ước tính doanh thu.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Mapping

from .validators import optional_text, to_float, to_int


@dataclass(frozen=True)
class AdCreative:
    """Nội dung một mẫu quảng cáo mô phỏng."""

    sponsor: str
    headline: str
    message: str
    hue: int


class AdSession:
    """Một lượt bắt đầu xem quảng cáo – lưu thời điểm bắt đầu để kiểm tra xem đủ thời lượng."""

    def __init__(self, *, viewer_id: str, creative: AdCreative, started_at: datetime) -> None:
        self._token = uuid.uuid4().hex
        self._viewer_id = viewer_id
        self._creative = creative
        self._started_at = started_at

    @property
    def token(self) -> str:
        return self._token

    @property
    def viewer_id(self) -> str:
        return self._viewer_id

    @property
    def creative(self) -> AdCreative:
        return self._creative

    @property
    def started_at(self) -> datetime:
        return self._started_at

    def seconds_watched(self, now: datetime) -> float:
        return (now - self._started_at).total_seconds()

    def is_stale(self, now: datetime, max_age: timedelta) -> bool:
        return now - self._started_at > max_age


class AdSettings:
    """Cấu hình quảng cáo: thời lượng bắt buộc xem và doanh thu ước tính mỗi lượt."""

    def __init__(self, *, duration_seconds: int | str = 15, revenue_per_view: float | str = 50) -> None:
        self.duration_seconds = duration_seconds
        self.revenue_per_view = revenue_per_view

    @property
    def duration_seconds(self) -> int:
        return self._duration_seconds

    @duration_seconds.setter
    def duration_seconds(self, value: int | str) -> None:
        seconds = to_int(value, "Thời lượng quảng cáo (giây)", minimum=5)
        self._duration_seconds = min(seconds, 120)

    @property
    def revenue_per_view(self) -> float:
        return self._revenue_per_view

    @revenue_per_view.setter
    def revenue_per_view(self, value: float | str) -> None:
        self._revenue_per_view = to_float(value, "Doanh thu ước tính mỗi lượt xem")

    def to_dict(self) -> dict[str, Any]:
        return {"duration_seconds": self._duration_seconds, "revenue_per_view": self._revenue_per_view}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdSettings":
        defaults = cls().to_dict()
        return cls(**{**defaults, **{k: v for k, v in data.items() if k in defaults}})


class AdLedger:
    """Sổ ghi lượt xem quảng cáo hợp lệ theo ngày."""

    def __init__(self, views_by_day: Mapping[str, int] | None = None) -> None:
        self._views: dict[str, int] = {}
        for day, count in (views_by_day or {}).items():
            self._views[optional_text(day)] = to_int(count, "Số lượt xem")

    def record(self, when: datetime) -> None:
        key = when.date().isoformat()
        self._views[key] = self._views.get(key, 0) + 1

    @property
    def total_views(self) -> int:
        return sum(self._views.values())

    def views_on(self, day: date) -> int:
        return self._views.get(day.isoformat(), 0)

    def recent(self, today: date, days: int = 7) -> list[tuple[date, int]]:
        return [(d, self.views_on(d)) for d in (today - timedelta(days=i) for i in range(days - 1, -1, -1))]

    def to_dict(self) -> dict[str, int]:
        return dict(sorted(self._views.items()))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdLedger":
        return cls(data)
