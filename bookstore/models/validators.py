"""Hàm kiểm tra & chuẩn hóa dữ liệu dùng chung cho các setter (phục vụ tính đóng gói)."""

from __future__ import annotations

from ..exceptions import ValidationError


def optional_text(value: object) -> str:
    """Chuyển về chuỗi đã cắt khoảng trắng; ``None`` thành chuỗi rỗng."""
    return "" if value is None else str(value).strip()


def require_text(value: object, label: str) -> str:
    text = optional_text(value)
    if not text:
        raise ValidationError(f"{label} không được để trống")
    return text


def _parse_number(value: object, label: str) -> float:
    text = optional_text(value).replace("_", "").replace(" ", "")
    if not text:
        raise ValidationError(f"{label} không được để trống")
    try:
        return float(text)
    except ValueError:
        raise ValidationError(f"{label} phải là một số (nhận được '{value}')") from None


def to_float(value: object, label: str, minimum: float = 0.0) -> float:
    number = _parse_number(value, label)
    if number < minimum:
        raise ValidationError(f"{label} phải lớn hơn hoặc bằng {minimum:g}")
    return number


def to_int(value: object, label: str, minimum: int = 0) -> int:
    number = _parse_number(value, label)
    if not number.is_integer():
        raise ValidationError(f"{label} phải là số nguyên")
    if number < minimum:
        raise ValidationError(f"{label} phải lớn hơn hoặc bằng {minimum}")
    return int(number)
