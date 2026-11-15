"""Tiện ích dùng chung cho các view: lấy Bookstore, người dùng hiện tại, decorator phân quyền."""

from __future__ import annotations

import uuid
from functools import wraps
from typing import Any, Callable

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from ..models import Account, Customer
from ..services import Bookstore


def get_store() -> Bookstore:
    return current_app.extensions["bookstore"]


def current_account() -> Account | None:
    if "account" not in g:
        g.account = get_store().accounts.find(session.get("account_id"))
    return g.account


def current_customer() -> Customer | None:
    if "customer" not in g:
        g.customer = get_store().accounts.customer_of(current_account())
    return g.customer


def visitor_id() -> str:
    """Mã định danh ẩn danh của trình duyệt (dùng cho lượt xem quảng cáo, kể cả khi chưa đăng nhập)."""
    if "visitor_id" not in session:
        session["visitor_id"] = uuid.uuid4().hex
    return session["visitor_id"]


def login_user(account: Account) -> None:
    """Tạo phiên mới khi đăng nhập (tránh session fixation) nhưng giữ lại giỏ hàng."""
    kept = {key: session[key] for key in ("cart", "visitor_id") if key in session}
    session.clear()
    session.update(kept)
    session["account_id"] = account.id
    g.pop("account", None)
    g.pop("customer", None)


def logout_user() -> None:
    session.clear()
    g.pop("account", None)
    g.pop("customer", None)


def safe_next(target: str | None, fallback: str) -> str:
    """Chỉ cho phép chuyển hướng tới đường dẫn nội bộ."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return fallback


def _login_redirect():
    flash("Vui lòng đăng nhập để tiếp tục.", "info")
    return redirect(url_for("accounts.login", next=request.full_path.rstrip("?")))


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_account() is None:
            return _login_redirect()
        return view(*args, **kwargs)

    return wrapped


def customer_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_account() is None:
            return _login_redirect()
        if current_customer() is None:
            flash("Chức năng này dành cho tài khoản khách hàng.", "info")
            return redirect(url_for("shop.index"))
        return view(*args, **kwargs)

    return wrapped


def require_admin() -> Any:
    """Dùng trong ``before_request`` của blueprint quản trị."""
    account = current_account()
    if account is None:
        return _login_redirect()
    if not account.is_admin:
        abort(403)
    return None
