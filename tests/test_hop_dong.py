from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from flask import template_rendered
from jinja2 import DictLoader, StrictUndefined

from nha_sach import create_app
from tests.hop_dong import CHUNG, KHACH, LOI, QUAN_LY


def kiem_hop_dong(kiem, thu_muc_template=None):
    with TemporaryDirectory() as thu_muc:
        app = create_app({
            "TESTING": True, "NHA_SACH_DB": Path(thu_muc) / "test.db",
            "NAP_DU_LIEU_MAU": True, **(
                {"template_folder": str(thu_muc_template)} if thu_muc_template else {}
            ),
        })
        app.jinja_env.undefined = StrictUndefined
        if not thu_muc_template:
            app.jinja_loader = DictLoader({
                ca.tep: " ".join("{{ " + ten + " is defined }}" for ten in ca.bien.split())
                for ca in (*KHACH, *QUAN_LY, *LOI)
            })
        ma_don = app.extensions["nha_sach_quan_ly"].lay_don(1).ma_tra_cuu
        khach = app.test_client()
        with khach.session_transaction() as phien:
            phien.update(
                ma_khach=1, don_da_xac_minh=[ma_don], csrf="kiem-hop-dong",
                ma_thao_tac_dat_hang="ma-thao-tac-kiem-hop-dong",
            )
        quan_ly = app.test_client()
        with quan_ly.session_transaction() as phien:
            phien["csrf"] = "quan-ly-hop-dong"
        quan_ly.post("/quan-ly/dang-nhap", data={"csrf": "quan-ly-hop-dong", "mat_khau": "admin"})

        def kiem_ca(ca, phan_hoi, su_kien):
            kiem.assertEqual(phan_hoi.status_code, ca.ma)
            kiem.assertEqual(su_kien[0][0], ca.tep)
            kiem.assertEqual(set(su_kien[0][1]) - {"g", "session"}, CHUNG | set(ca.bien.split()))

        su_kien = []
        def da_render(sender, template, context):
            su_kien.append((template.name, context))

        with template_rendered.connected_to(da_render, app):
            for ca in (*KHACH, *QUAN_LY):
                with kiem.subTest(duong_dan=ca.duong_dan):
                    su_kien.clear()
                    client = quan_ly if ca in QUAN_LY else khach
                    kiem_ca(ca, client.get(ca.duong_dan.format(ma_tra_cuu=ma_don)), su_kien)

            for ca, form in zip(LOI, (
                {"csrf": "kiem-hop-dong", "ma_thao_tac": "ma-thao-tac-kiem-hop-dong"},
                {"csrf": "kiem-hop-dong", "ma": "KHONGBIET", "dien_thoai": "0901234567"},
                {},
            ), strict=True):
                with kiem.subTest(post=ca.duong_dan):
                    su_kien.clear()
                    kiem_ca(ca, khach.post(ca.duong_dan, data=form), su_kien)


class TestHopDong(unittest.TestCase):
    def test_template_va_bien(self):
        kiem_hop_dong(self)
