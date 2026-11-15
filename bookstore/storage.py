"""Lưu trữ dữ liệu – tách khỏi nghiệp vụ qua lớp trừu tượng ``DataStorage``.

    DataStorage (trừu tượng)
    ├── InMemoryStorage        – lưu trong bộ nhớ, dùng cho kiểm thử
    └── FileStorage (trừu tượng) – có đường dẫn file, sao lưu được khi file hỏng
        ├── JsonFileStorage    – một file JSON, ghi lại toàn bộ mỗi lần lưu
        └── SqliteStorage      – CSDL SQLite, chỉ ghi các dòng thay đổi, trong một transaction

Nhờ vậy đổi cách lưu không phải sửa bất kỳ dòng nào trong tầng nghiệp vụ.
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .exceptions import DataCorruptedError


@dataclass(frozen=True)
class ChangeSet:
    """Những gì thay đổi sau một lệnh (do ``UnitOfWork`` gom lại).

    - ``keys``:     danh sách mã hiện có của từng bảng (để biết dòng nào đã bị xóa)
    - ``dirty``:    chỉ các đối tượng đã thay đổi, ở dạng dict
    - ``settings``: các cấu hình nhỏ (kho Drive, quảng cáo…) – luôn ghi
    - ``snapshot``: hàm trả về toàn bộ dữ liệu, cho kiểu lưu không hỗ trợ ghi một phần
    """

    keys: dict[str, list[str]]
    dirty: dict[str, dict[str, dict[str, Any]]]
    settings: dict[str, Any]
    snapshot: Callable[[], dict[str, Any]] = field(repr=False)

    @property
    def dirty_count(self) -> int:
        return sum(len(items) for items in self.dirty.values())


class DataStorage(ABC):
    """Giao diện lưu/đọc toàn bộ dữ liệu nhà sách dưới dạng dict."""

    @abstractmethod
    def load(self) -> dict[str, Any] | None:
        """Trả về dữ liệu đã lưu, hoặc ``None`` nếu chưa có."""

    @abstractmethod
    def save(self, data: dict[str, Any]) -> None:
        """Ghi toàn bộ dữ liệu."""

    def save_changes(self, changes: ChangeSet) -> None:
        """Ghi các thay đổi. Mặc định ghi lại toàn bộ; lớp con hỗ trợ ghi một phần thì ghi đè."""
        self.save(changes.snapshot())


class InMemoryStorage(DataStorage):
    """Lưu trong bộ nhớ – dùng cho kiểm thử."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = copy.deepcopy(data)

    def load(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._data)

    def save(self, data: dict[str, Any]) -> None:
        self._data = copy.deepcopy(data)


class FileStorage(DataStorage):
    """Lưu trữ dựa trên một file trên đĩa."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists()

    def move_aside(self) -> Path:
        """Đổi tên file lỗi thành bản sao lưu để tạo dữ liệu mới mà không mất file cũ."""
        backup = self._path.with_name(f"{self._path.stem}.loi-{datetime.now():%Y%m%d-%H%M%S}{self._path.suffix}")
        os.replace(self._path, backup)
        return backup


class JsonFileStorage(FileStorage):
    """Lưu vào file JSON; ghi qua file tạm rồi thay thế để không bao giờ để lại file ghi dở."""

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DataCorruptedError(f"Không đọc được file dữ liệu {self._path.name}: {error}") from error
        if not isinstance(data, dict):
            raise DataCorruptedError(f"File {self._path.name} không đúng cấu trúc")
        return data

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, self._path)


class SqliteStorage(FileStorage):
    """Lưu vào SQLite: mỗi danh sách (sách, khách, đơn…) là một bảng, mỗi đối tượng là một dòng.

    Khi lưu, so sánh với dữ liệu đang có trong CSDL và chỉ INSERT / UPDATE / DELETE các dòng
    thay đổi; tất cả nằm trong một transaction nên hoặc ghi hết, hoặc không ghi gì.
    """

    COLLECTIONS: dict[str, str] = {  # tên bảng -> khóa định danh của đối tượng
        "products": "id",
        "customers": "id",
        "accounts": "id",
        "orders": "id",
        "vouchers": "code",
    }

    def __init__(self, path: str | Path) -> None:
        super().__init__(path)
        self.last_changes: dict[str, int] = {"inserted": 0, "updated": 0, "deleted": 0}

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._path)

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        for table in self.COLLECTIONS:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                "id TEXT PRIMARY KEY, seq INTEGER NOT NULL, data TEXT NOT NULL)"
            )
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, data TEXT NOT NULL)")

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        try:
            with closing(self._connect()) as conn:
                self._ensure_schema(conn)
                data: dict[str, Any] = {
                    key: json.loads(value) for key, value in conn.execute("SELECT key, data FROM settings")
                }
                if "version" not in data:
                    return None  # CSDL rỗng
                for table in self.COLLECTIONS:
                    rows = conn.execute(f"SELECT data FROM {table} ORDER BY seq")
                    data[table] = [json.loads(row[0]) for row in rows]
                return data
        except (sqlite3.DatabaseError, json.JSONDecodeError) as error:
            raise DataCorruptedError(f"Không đọc được CSDL {self._path.name}: {error}") from error

    def save(self, data: dict[str, Any]) -> None:
        """Thay thế TOÀN BỘ dữ liệu (dùng khi tạo mới, đặt lại dữ liệu mẫu, chuyển từ JSON sang).

        Xóa sạch rồi ghi lại theo đúng thứ tự trong ``data`` để thứ tự đọc lên khớp với bộ nhớ.
        """
        stats = {"inserted": 0, "updated": 0, "deleted": 0}
        with closing(self._connect()) as conn, conn:  # `with conn` = một transaction
            self._ensure_schema(conn)
            for table, key_field in self.COLLECTIONS.items():
                stats["deleted"] += conn.execute(f"DELETE FROM {table}").rowcount
                rows = [
                    (str(item[key_field]), seq, json.dumps(item, ensure_ascii=False, sort_keys=True))
                    for seq, item in enumerate(data.get(table, []), start=1)
                ]
                conn.executemany(f"INSERT INTO {table} (id, seq, data) VALUES (?, ?, ?)", rows)
                stats["inserted"] += len(rows)
            self._save_settings(conn, {k: v for k, v in data.items() if k not in self.COLLECTIONS})
        self.last_changes = stats

    def save_changes(self, changes: ChangeSet) -> None:
        """Chỉ ghi các đối tượng đã thay đổi (Unit of Work) – không phải chuyển cả kho sang JSON."""
        stats = {"inserted": 0, "updated": 0, "deleted": 0}
        with closing(self._connect()) as conn, conn:
            self._ensure_schema(conn)
            for table in self.COLLECTIONS:
                current_keys = changes.keys.get(table, [])
                dirty = changes.dirty.get(table, {})
                existing = {row[0] for row in conn.execute(f"SELECT id FROM {table}")}

                removed = existing - set(current_keys)
                conn.executemany(f"DELETE FROM {table} WHERE id = ?", [(key,) for key in removed])
                stats["deleted"] += len(removed)

                next_seq = conn.execute(f"SELECT COALESCE(MAX(seq), 0) + 1 FROM {table}").fetchone()[0]
                for key in current_keys:
                    if key in dirty:
                        payload = json.dumps(dirty[key], ensure_ascii=False, sort_keys=True)
                        if key in existing:
                            conn.execute(f"UPDATE {table} SET data = ? WHERE id = ?", (payload, key))
                            stats["updated"] += 1
                        else:
                            conn.execute(f"INSERT INTO {table} (id, seq, data) VALUES (?, ?, ?)",
                                         (key, next_seq, payload))
                            next_seq += 1
                            stats["inserted"] += 1
                    elif key not in existing:
                        # Đối tượng mới luôn "bẩn"; tới đây nghĩa là có lỗi lập trình → hủy cả transaction.
                        raise RuntimeError(f"Thiếu dữ liệu của '{key}' trong bảng {table}")
            self._save_settings(conn, changes.settings)
        self.last_changes = stats

    def _save_settings(self, conn: sqlite3.Connection, settings: dict[str, Any]) -> None:
        for key, value in settings.items():
            conn.execute(
                "INSERT INTO settings (key, data) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET data = excluded.data",
                (key, json.dumps(value, ensure_ascii=False)),
            )
