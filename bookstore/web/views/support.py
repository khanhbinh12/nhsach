"""Ủng hộ web bằng cách xem quảng cáo (mô phỏng). Không mở khóa nội dung."""

from __future__ import annotations

import math

from flask import Blueprint, flash, redirect, render_template, session, url_for

from ..context import get_store, visitor_id

bp = Blueprint("support", __name__, url_prefix="/ung-ho")

TOKEN_KEY = "ad_token"


@bp.get("/")
def index():
    store = get_store()
    ledger = store.ads.ledger
    return render_template(
        "support/index.html",
        total_views=ledger.total_views,
        today_views=ledger.views_on(store.now().date()),
        duration=store.ads.settings.duration_seconds,
    )


@bp.post("/xem")
def start():
    ad_session = get_store().start_ad(visitor_id())
    session[TOKEN_KEY] = ad_session.token
    return redirect(url_for(".watch"))


@bp.get("/xem")
def watch():
    store = get_store()
    ad_session = store.ads.find_session(session.get(TOKEN_KEY), visitor_id())
    if ad_session is None:
        return redirect(url_for(".index"))
    duration = store.ads.settings.duration_seconds
    remaining = max(0, math.ceil(duration - ad_session.seconds_watched(store.now())))
    return render_template("support/watch.html", ad=ad_session.creative, duration=duration, remaining=remaining)


@bp.post("/hoan-tat")
def complete():
    total = get_store().complete_ad(session.get(TOKEN_KEY), visitor_id())
    session.pop(TOKEN_KEY, None)
    flash(f"Cảm ơn bạn đã ủng hộ Nhà Sách Trí Tri! Web đã nhận tổng cộng {total} lượt ủng hộ.", "success")
    return redirect(url_for(".index"))
