"""Bảo mật tầng web: chống CSRF cho mọi form POST và gắn các header bảo mật cho mọi phản hồi."""

from __future__ import annotations

import hmac
import secrets

from flask import Flask, abort, current_app, request, session
from markupsafe import Markup


class CsrfProtection:
    """Mỗi phiên có một token bí mật; mọi request POST phải gửi kèm đúng token đó."""

    SESSION_KEY = "_csrf_token"
    FORM_FIELD = "csrf_token"

    def __init__(self, app: Flask | None = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.config.setdefault("CSRF_ENABLED", True)
        app.before_request(self._protect)
        app.jinja_env.globals["csrf_field"] = self.hidden_field

    @classmethod
    def token(cls) -> str:
        if cls.SESSION_KEY not in session:
            session[cls.SESSION_KEY] = secrets.token_hex(16)
        return session[cls.SESSION_KEY]

    @classmethod
    def hidden_field(cls) -> Markup:
        return Markup(f'<input type="hidden" name="{cls.FORM_FIELD}" value="{cls.token()}">')

    def _protect(self) -> None:
        if request.method != "POST" or not current_app.config["CSRF_ENABLED"]:
            return
        sent = request.form.get(self.FORM_FIELD, "")
        expected = session.get(self.SESSION_KEY, "")
        if not sent or not expected or not hmac.compare_digest(sent, expected):
            abort(400)


class SecurityHeaders:
    """Header bảo mật cho mọi phản hồi.

    - Content-Security-Policy: chỉ chạy JavaScript từ file của chính web (``app.js``) – script chèn lén
      vào trang (XSS) sẽ bị trình duyệt chặn. ``style-src 'unsafe-inline'`` cần cho màu bìa sách vẽ tự động.
    - X-Frame-Options / frame-ancestors: không cho web khác nhúng trang vào iframe (chống clickjacking).
    - X-Content-Type-Options: trình duyệt không được tự "đoán" kiểu file.
    """

    POLICY = "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
    ])
    HEADERS = {
        "Content-Security-Policy": POLICY,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    def __init__(self, app: Flask | None = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.after_request(self._apply)

    def _apply(self, response):
        for name, value in self.HEADERS.items():
            response.headers.setdefault(name, value)
        return response
