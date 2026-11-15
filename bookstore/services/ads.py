"""Dịch vụ quảng cáo ủng hộ web (mô phỏng) – chỉ ghi nhận lượt xem, không mở khóa nội dung."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping

from ..exceptions import ValidationError
from ..models import AdCreative, AdLedger, AdSession, AdSettings


class AdService:
    SESSION_MAX_AGE = timedelta(hours=1)
    CREATIVES = (
        AdCreative("Cà phê Sách Xanh", "Mua 1 tặng 1 mỗi sáng thứ Hai", "Không gian đọc sách yên tĩnh giữa lòng thành phố.", 150),
        AdCreative("Bút Mực Hồng Hà", "Bộ bút ký sinh viên chỉ 59.000đ", "Viết êm, nhanh khô, phù hợp ghi chép mỗi ngày.", 210),
        AdCreative("Đèn Học Ánh Dương", "Đèn chống cận cho mùa ôn thi", "Ánh sáng dịu mắt, điều chỉnh 3 mức độ sáng.", 40),
        AdCreative("Khóa học Tiếng Anh Mỗi Ngày", "Học thử miễn phí 7 ngày", "Lộ trình 15 phút/ngày cho người bận rộn.", 280),
    )

    def __init__(self, settings: AdSettings, ledger: AdLedger, clock: Callable[[], datetime] = datetime.now) -> None:
        self._settings = settings
        self._ledger = ledger
        self._clock = clock
        self._sessions: dict[str, AdSession] = {}

    @property
    def settings(self) -> AdSettings:
        return self._settings

    @property
    def ledger(self) -> AdLedger:
        return self._ledger

    def update_settings(self, changes: Mapping[str, Any]) -> AdSettings:
        self._settings = AdSettings.from_dict({**self._settings.to_dict(), **changes})
        return self._settings

    def estimated_revenue(self) -> float:
        return self._ledger.total_views * self._settings.revenue_per_view

    def start(self, viewer_id: str) -> AdSession:
        now = self._clock()
        self._sessions = {t: s for t, s in self._sessions.items() if not s.is_stale(now, self.SESSION_MAX_AGE)}
        session = AdSession(viewer_id=viewer_id, creative=random.choice(self.CREATIVES), started_at=now)
        self._sessions[session.token] = session
        return session

    def find_session(self, token: str | None, viewer_id: str) -> AdSession | None:
        session = self._sessions.get(token or "")
        return session if session is not None and session.viewer_id == viewer_id else None

    def complete(self, token: str | None, viewer_id: str) -> int:
        """Ghi nhận lượt xem nếu đã xem đủ thời lượng; trả về tổng lượt xem."""
        session = self.find_session(token, viewer_id)
        if session is None:
            raise ValidationError("Phiên xem quảng cáo không hợp lệ hoặc đã hết hạn")
        now = self._clock()
        watched = session.seconds_watched(now)
        if watched < self._settings.duration_seconds:
            raise ValidationError(
                f"Bạn cần xem đủ {self._settings.duration_seconds} giây (mới xem {int(watched)} giây)"
            )
        del self._sessions[session.token]
        self._ledger.record(now)
        return self._ledger.total_views
