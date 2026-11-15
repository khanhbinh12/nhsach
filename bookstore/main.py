"""Điểm khởi động web: python run.py  (hoặc python -m bookstore).

Biến môi trường (tùy chọn):
    PORT=5000                  cổng chạy web
    BOOKSTORE_STORAGE=json     lưu bằng file JSON thay cho SQLite (mặc định)
    BOOKSTORE_SECRET_KEY=...   khóa ký cookie phiên
    BOOKSTORE_DEV=1            dùng server phát triển của Flask thay cho waitress
"""

from __future__ import annotations

import logging
import os
import secrets
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .exceptions import DataCorruptedError
from .services import Bookstore, CoverImageStore
from .services.seed import ADMIN_LOGIN, ADMIN_PASSWORD, DEMO_PASSWORD
from .storage import FileStorage, JsonFileStorage, SqliteStorage
from .web import create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQLITE_FILE = DATA_DIR / "bookstore.db"
JSON_FILE = DATA_DIR / "bookstore.json"
UPLOAD_DIR = DATA_DIR / "uploads" / "covers"
LOG_DIR = DATA_DIR / "logs"
SECRET_FILE = DATA_DIR / "secret_key.txt"


def create_storage() -> FileStorage:
    """Chọn cách lưu; lần đầu chuyển sang SQLite thì tự nhập dữ liệu từ file JSON cũ (nếu có)."""
    if os.environ.get("BOOKSTORE_STORAGE", "sqlite").lower() == "json":
        return JsonFileStorage(JSON_FILE)
    storage = SqliteStorage(SQLITE_FILE)
    if not storage.exists() and JSON_FILE.exists():
        try:
            data = JsonFileStorage(JSON_FILE).load()
        except DataCorruptedError as error:
            print(f"[!] Bỏ qua file JSON cũ bị lỗi: {error}")
        else:
            storage.save(data)
            JSON_FILE.rename(JSON_FILE.with_suffix(".json.da-chuyen-sang-sqlite"))
            print("[i] Đã chuyển dữ liệu từ bookstore.json sang SQLite (bookstore.db).")
    return storage


def open_bookstore(storage: FileStorage, media: CoverImageStore) -> Bookstore:
    """Mở dữ liệu; nếu file hỏng / khác phiên bản thì sao lưu file cũ rồi tạo dữ liệu mẫu mới."""
    try:
        return Bookstore(storage, media=media)
    except DataCorruptedError as error:
        backup = storage.move_aside()
        print(f"[!] {error}\n[!] Đã sao lưu dữ liệu cũ tại: {backup}\n[!] Tạo dữ liệu mẫu mới.")
        return Bookstore(storage, media=media)


def setup_logging() -> Path:
    """Ghi log ra màn hình và file xoay vòng (tối đa 5 file × 1 MB) để biết web gặp lỗi gì, khi nào."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "bookstore.log"
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    console_handler = logging.StreamHandler()
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
    for name in ("bookstore", "waitress"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.handlers[:] = [file_handler, console_handler]
        logger.propagate = False
    return log_file


def load_secret_key() -> str:
    """Khóa bí mật ký cookie phiên – lưu lại để khởi động lại server không bị đăng xuất."""
    if os.environ.get("BOOKSTORE_SECRET_KEY"):
        return os.environ["BOOKSTORE_SECRET_KEY"]
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    SECRET_FILE.write_text(key, encoding="utf-8")
    return key


def main() -> None:
    log_file = setup_logging()
    logging.getLogger("bookstore").info("Khởi động Nhà Sách Trí Tri – log ghi tại %s", log_file)
    storage = create_storage()
    store = open_bookstore(storage, CoverImageStore(UPLOAD_DIR))
    app = create_app(store, secret_key=load_secret_key())
    port = int(os.environ.get("PORT", "5000"))
    dev_mode = os.environ.get("BOOKSTORE_DEV") == "1"
    print(
        "\n  Nhà Sách Trí Tri đang chạy tại  http://127.0.0.1:%d   (dữ liệu: %s, máy chủ: %s)\n"
        "  Quản trị: %s / %s     Khách demo: nam.nt@example.com / %s\n"
        "  Nhấn Ctrl+C để dừng.\n"
        % (port, storage.path.name, "Flask dev" if dev_mode else "waitress", ADMIN_LOGIN, ADMIN_PASSWORD,
           DEMO_PASSWORD)
    )
    if dev_mode:
        app.run(host="127.0.0.1", port=port, debug=False)
    else:
        from waitress import serve

        # waitress: máy chủ WSGI cho môi trường thật, xử lý nhiều request song song bằng nhiều luồng
        # (an toàn vì mọi lệnh ghi của Bookstore đều chạy trong khóa).
        serve(app, host="127.0.0.1", port=port, threads=8, ident="NhaSachTriTri")
