"""Unit of Work: sau mỗi lệnh, gom các đối tượng đã thay đổi và ghi xuống kho lưu trữ một lần.

Trước đây mỗi lệnh ghi phải chuyển TOÀN BỘ dữ liệu sang dict rồi so với CSDL (~110 ms khi có
~2.000 sách và ~3.000 đơn). Nay chỉ các đối tượng đã đánh dấu thay đổi (``Trackable.is_dirty``)
mới được chuyển và ghi.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from ..models.tracking import Trackable
from ..storage import ChangeSet, DataStorage


class UnitOfWork:
    def __init__(
        self,
        collections: Mapping[str, Callable[[], Iterable[Trackable]]],
        key_fields: Mapping[str, str],
        settings: Callable[[], dict[str, Any]],
        snapshot: Callable[[], dict[str, Any]],
    ) -> None:
        self._collections = collections
        self._key_fields = key_fields
        self._settings = settings
        self._snapshot = snapshot

    def collect(self) -> ChangeSet:
        keys: dict[str, list[str]] = {}
        dirty: dict[str, dict[str, dict[str, Any]]] = {}
        for name, provider in self._collections.items():
            field = self._key_fields[name]
            objects = list(provider())
            keys[name] = [getattr(obj, field) for obj in objects]
            dirty[name] = {getattr(obj, field): obj.to_dict() for obj in objects if obj.is_dirty}
        return ChangeSet(keys=keys, dirty=dirty, settings=self._settings(), snapshot=self._snapshot)

    def commit(self, storage: DataStorage) -> ChangeSet:
        """Ghi thay đổi; chỉ khi ghi thành công mới xóa dấu "đã thay đổi"."""
        changes = self.collect()
        storage.save_changes(changes)
        self.mark_clean()
        return changes

    def mark_clean(self) -> None:
        for provider in self._collections.values():
            for obj in provider():
                obj.mark_clean()
