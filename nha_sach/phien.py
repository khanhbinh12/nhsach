"""Giới hạn thử và quản lý phiên trong tiến trình Flask."""
from collections import deque
from secrets import token_urlsafe
from threading import Lock
from time import monotonic


class GioiHanThu:
    def __init__(self, so_lan=5, so_giay=900):
        self.so_lan = so_lan
        self.so_giay = so_giay
        self._thu = {}
        self._den = {}
        self._khoa = Lock()

    def ghi_nhan(self, khoa):
        luc = monotonic()
        with self._khoa:
            self._den = {k: v for k, v in self._den.items() if v > luc}
            if khoa in self._den:
                return False
            het_han = luc - self.so_giay
            self._thu = {k: v for k, v in self._thu.items() if v[-1] > het_han}
            thu = self._thu.setdefault(khoa, deque())
            while thu and thu[0] <= het_han:
                thu.popleft()
            thu.append(luc)
            if len(thu) >= self.so_lan:
                self._den[khoa] = luc + self.so_giay
                self._thu.pop(khoa)
            return True

    def xoa(self, khoa):
        with self._khoa:
            self._thu.pop(khoa, None)
            self._den.pop(khoa, None)


class PhienQuanLy:
    def __init__(self):
        self._han = {}
        self._khoa = Lock()

    def tao(self):
        ma = token_urlsafe(32)
        luc = monotonic()
        with self._khoa:
            self._han = {k: v for k, v in self._han.items() if v > luc}
            self._han[ma] = luc + 7200
        return ma

    def hop_le(self, ma):
        if not isinstance(ma, str):
            return False
        with self._khoa:
            return self._han.get(ma, 0) > monotonic()

    def xoa(self, ma):
        if isinstance(ma, str):
            with self._khoa:
                self._han.pop(ma, None)
