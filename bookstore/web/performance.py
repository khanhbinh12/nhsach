"""Tối ưu tải trang: lưu đệm file tĩnh dài hạn và nén gzip trang HTML."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

from flask import Flask, Response, request, url_for


class StaticAssets:
    """Sinh đường dẫn file tĩnh kèm dấu phiên bản, ví dụ ``/static/style.css?v=3f9a1c0b2d``.

    Trình duyệt được phép lưu đệm file tĩnh 1 năm (không phải tải lại CSS mỗi trang); khi file
    thay đổi thì mã băm đổi → đường dẫn đổi → trình duyệt tự tải bản mới.
    """

    CACHE_SECONDS = 365 * 24 * 3600

    def __init__(self, app: Flask | None = None) -> None:
        self._versions: dict[tuple[str, float], str] = {}
        self._folder: Path | None = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = self.CACHE_SECONDS
        self._folder = Path(app.static_folder)
        app.jinja_env.globals["asset_url"] = self.url

    def version(self, filename: str) -> str:
        path = self._folder / filename
        key = (filename, path.stat().st_mtime)
        if key not in self._versions:  # chỉ băm lại khi file được sửa
            self._versions[key] = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
        return self._versions[key]

    def url(self, filename: str) -> str:
        return url_for("static", filename=filename, v=self.version(filename))


class GzipCompression:
    """Nén gzip các phản hồi dạng văn bản khi trình duyệt hỗ trợ (giảm ~70–80% dung lượng HTML)."""

    MIN_SIZE = 500
    COMPRESSIBLE = {"text/html", "text/css", "text/plain", "application/json", "application/javascript",
                    "text/javascript", "image/svg+xml"}

    def __init__(self, app: Flask | None = None, level: int = 6) -> None:
        self._level = level
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.after_request(self._compress)

    def _compress(self, response: Response) -> Response:
        if (
            "gzip" not in request.headers.get("Accept-Encoding", "").lower()
            or response.status_code != 200
            or response.direct_passthrough  # file gửi thẳng từ đĩa (CSS, ảnh): đã được lưu đệm dài hạn
            or "Content-Encoding" in response.headers
            or response.mimetype not in self.COMPRESSIBLE
        ):
            return response
        data = response.get_data()
        if len(data) < self.MIN_SIZE:
            return response
        response.set_data(gzip.compress(data, compresslevel=self._level))
        response.headers["Content-Encoding"] = "gzip"
        response.vary.add("Accept-Encoding")
        return response
