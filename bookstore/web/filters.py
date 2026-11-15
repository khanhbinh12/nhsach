"""Bộ lọc Jinja dùng trong template."""

from __future__ import annotations

import zlib
from datetime import date, datetime

from flask import Flask


def vnd(amount: float) -> str:
    return f"{amount:,.0f} ₫".replace(",", ".")


def datetime_vn(value: datetime | date | None, with_time: bool = True) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime) and with_time:
        return value.strftime("%d/%m/%Y %H:%M")
    return value.strftime("%d/%m/%Y")


def hue(text: str) -> int:
    """Màu bìa sách ổn định theo mã sách (0–359)."""
    return zlib.crc32(text.encode("utf-8")) % 360


def percent(rate: float) -> str:
    return f"{rate * 100:g}%"


def register_filters(app: Flask) -> None:
    app.jinja_env.filters.update(vnd=vnd, dt=datetime_vn, hue=hue, percent=percent)
