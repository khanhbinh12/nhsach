"""Phục vụ ảnh bìa sách đã tải lên."""

from __future__ import annotations

import mimetypes

from flask import Blueprint, abort, send_from_directory

from ..context import get_store

# Windows thường không đăng ký đuôi .webp → nếu thiếu dòng này ảnh bị gửi với kiểu application/octet-stream.
mimetypes.add_type("image/webp", ".webp")

bp = Blueprint("media", __name__)


@bp.get("/anh-bia/<path:filename>")
def cover(filename: str):
    media = get_store().media
    if media is None:
        abort(404)
    # send_from_directory tự chặn đường dẫn kiểu ../ ra ngoài thư mục ảnh
    return send_from_directory(media.folder, filename, max_age=86400)
