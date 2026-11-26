from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nha_sach.du_lieu import doc_du_lieu_mau, nap_mau
from nha_sach.dich_vu import DichVuQuanLy
from nha_sach.kho import CoSoDuLieu


SACH_MAU = Path(__file__).resolve().parents[1] / "du_lieu" / "sach_mau.json"


class TestDuLieu(unittest.TestCase):
    def test_tep_mau_hop_le(self):
        du_lieu = doc_du_lieu_mau(SACH_MAU)
        self.assertEqual(len(du_lieu["sach"]), 50)
        self.assertTrue(du_lieu["danh_gia"])

    def test_nap_mau_mot_lan(self):
        with TemporaryDirectory() as tmp:
            csdl = CoSoDuLieu(Path(tmp) / "test.db")
            csdl.tao_bang()
            self.assertTrue(nap_mau(csdl, SACH_MAU))
            self.assertFalse(nap_mau(csdl, SACH_MAU))
            self.assertEqual(len(DichVuQuanLy(csdl).doanh_thu()), 15)
            with csdl.doc() as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM sach").fetchone()[0], 50)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM danh_gia").fetchone()[0], 15)
