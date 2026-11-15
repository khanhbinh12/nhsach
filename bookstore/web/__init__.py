"""Tầng web Flask.

``create_app()`` (Application Factory) nhận một ``Bookstore`` đã khởi tạo, nên khi kiểm thử có thể
truyền vào một Bookstore dùng ``InMemoryStorage``.
"""

from __future__ import annotations

import secrets
from urllib.parse import urlparse

from flask import Flask, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.exceptions import HTTPException

from ..exceptions import BookstoreError
from ..models import OrderStatus
from ..services import Bookstore
from .context import current_account, current_customer, get_store
from .filters import register_filters
from .pagination import page_url
from .performance import GzipCompression, StaticAssets
from .security import CsrfProtection, SecurityHeaders
from .session_cart import SessionCart


def create_app(store: Bookstore, *, secret_key: str | None = None, testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret_key or secrets.token_hex(32),
        TESTING=testing,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=3 * 1024 * 1024,  # giới hạn kích thước request (ảnh bìa tối đa 2 MB)
    )
    app.extensions["bookstore"] = store

    CsrfProtection(app)
    SecurityHeaders(app)
    StaticAssets(app)
    GzipCompression(app)
    register_filters(app)
    app.jinja_env.globals.update(page_url=page_url, cover_src=cover_src)
    app.add_url_rule("/favicon.ico", "favicon", _favicon)
    _register_blueprints(app)
    _register_context(app)
    _register_error_handlers(app)
    return app


def _favicon():
    """Trình duyệt luôn hỏi /favicon.ico – trước đây trả 404 và phải dựng cả trang báo lỗi."""
    return send_from_directory(current_app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")


def cover_src(book, size: str = "") -> str:
    """Ảnh bìa lớn cho trang chi tiết, ảnh thu nhỏ cho danh sách / giỏ hàng."""
    name = book.cover_image
    media = get_store().media
    if media is not None and size != "large":
        name = media.thumb_or_original(name)
    return url_for("media.cover", filename=name)


def _register_blueprints(app: Flask) -> None:
    from .views.accounts import bp as accounts_bp
    from .views.admin import bp as admin_bp
    from .views.library import bp as library_bp
    from .views.media import bp as media_bp
    from .views.shop import bp as shop_bp
    from .views.support import bp as support_bp

    for blueprint in (shop_bp, accounts_bp, library_bp, support_bp, admin_bp, media_bp):
        app.register_blueprint(blueprint)


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_globals() -> dict:
        store = get_store()
        account = current_account()
        customer = current_customer()
        return {
            "store": store,
            "current_account": account,
            "current_customer": customer,
            "display_name": customer.name if customer else (account.display_name if account else ""),
            "cart_count": SessionCart(store.inventory).count(),
            "pending_count": store.orders.count(OrderStatus.PENDING) if account and account.is_admin else 0,
            "OrderStatus": OrderStatus,
        }


def _same_site_referrer() -> str | None:
    referrer = request.referrer
    if referrer and urlparse(referrer).netloc == request.host:
        return referrer
    return None


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(BookstoreError)
    def handle_business_error(error: BookstoreError):
        """Lỗi nghiệp vụ: hiện thông báo và quay lại trang trước – không làm sập web."""
        flash(str(error), "error")
        return redirect(_same_site_referrer() or url_for("shop.index"))

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        messages = {
            400: "Yêu cầu không hợp lệ hoặc phiên làm việc đã hết hạn. Vui lòng thử lại.",
            403: "Bạn không có quyền truy cập trang này.",
            404: "Không tìm thấy trang bạn yêu cầu.",
            413: "File tải lên quá lớn – ảnh bìa tối đa 2 MB.",
        }
        message = messages.get(error.code or 500, error.description)
        return render_template("errors/error.html", code=error.code, message=message), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        """Lỗi ngoài dự kiến (bug): ghi đầy đủ vào log để sửa, người dùng chỉ thấy trang báo lỗi thân thiện."""
        account = current_account()
        current_app.logger.exception(
            "Lỗi không mong muốn tại %s %s (tài khoản: %s)",
            request.method, request.path, account.login if account else "khách",
        )
        message = "Đã có lỗi xảy ra phía máy chủ. Nhà sách đã ghi nhận và sẽ khắc phục sớm."
        return render_template("errors/error.html", code=500, message=message), 500
