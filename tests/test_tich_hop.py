import os
from pathlib import Path
import unittest

from tests.test_hop_dong import kiem_hop_dong


class TestTichHop(unittest.TestCase):
    def test_template_that(self):
        thu_muc = Path(os.environ.get(
            "NHA_SACH_TEMPLATE_TEST", Path(__file__).resolve().parents[1] / "templates",
        ))
        if not thu_muc.is_dir() and os.environ.get("NHA_SACH_TICH_HOP") != "1":
            self.skipTest("Chưa có thư mục templates.")
        self.assertTrue(thu_muc.is_dir(), f"Thiếu templates tích hợp: {thu_muc}")
        kiem_hop_dong(self, thu_muc)
