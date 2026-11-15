"""Chống dò mật khẩu (brute-force): sai quá nhiều lần trong một khoảng thời gian thì tạm khóa."""

from __future__ import annotations

import math
import threading
from datetime import datetime, timedelta
from typing import Callable

from ..exceptions import AuthenticationError


class LoginThrottle:
    """Đếm số lần đăng nhập sai theo một khóa (tên đăng nhập hoặc địa chỉ IP).

    Sai ``max_failures`` lần trong ``window`` → khóa khóa đó trong ``lockout``.
    Dữ liệu chỉ nằm trong bộ nhớ: khởi động lại máy chủ thì bộ đếm về 0.
    """

    def __init__(
        self,
        *,
        max_failures: int,
        window: timedelta,
        lockout: timedelta,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._max_failures = max_failures
        self._window = window
        self._lockout = lockout
        self._clock = clock
        self._failures: dict[str, list[datetime]] = {}
        self._locked_until: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def ensure_allowed(self, key: str) -> None:
        """Báo lỗi nếu ``key`` đang bị tạm khóa."""
        with self._lock:
            until = self._locked_until.get(key)
            now = self._clock()
            if until is None:
                return
            if now >= until:
                del self._locked_until[key]
                return
            minutes = max(1, math.ceil((until - now).total_seconds() / 60))
        raise AuthenticationError(f"Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {minutes} phút.")

    def record_failure(self, key: str) -> bool:
        """Ghi nhận một lần sai; trả về True nếu lần này khiến ``key`` bị khóa."""
        with self._lock:
            now = self._clock()
            recent = [t for t in self._failures.get(key, []) if now - t < self._window]
            recent.append(now)
            if len(recent) >= self._max_failures:
                self._locked_until[key] = now + self._lockout
                self._failures.pop(key, None)
                return True
            self._failures[key] = recent
            return False

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)
