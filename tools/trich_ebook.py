"""Trích dữ liệu EPUB tại máy và chọn sách bổ sung cho danh mục."""
import argparse
import json
from html import unescape
from io import BytesIO
from pathlib import Path, PurePosixPath
import posixpath
import re
import unicodedata
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import ZipFile

from PIL import Image, ImageOps


DANH_MUC = {
    "Biên Khảo": ("Biên khảo", "bien-khao"),
    "Bút Ký - Hồi Ký - Tự Truyện": ("Hồi ký", "hoi-ky"),
    "Kinh Doanh - Quản Trị": ("Kinh tế", "kinh-te"),
    "Kinh Dị - Trinh Thám": ("Trinh thám – Kinh dị", "trinh-tham-kinh-di"),
    "Lịch Sử Quân Sự": ("Lịch sử", "lich-su"),
    "Tham Khảo": ("Tham khảo", "tham-khao"),
    "Thiếu Nhi - Truyện Ngắn - Tản Văn": ("Thiếu nhi", "thieu-nhi"),
    "Tiểu Thuyết": ("Tiểu thuyết", "tieu-thuyet"),
    "Triết Học - Tâm Lý Học": ("Triết học", "triet-hoc"),
    "Văn Hoá - Xã Hội": ("Văn hóa – Xã hội", "van-hoa-xa-hoi"),
}
BO_QUA = re.compile(
    r"(?:^|[-_/ ])(?:cover|toc|nav|copyright|titlepage|colophon|imprint|"
    r"loi-gioi-thieu|loi-noi-dau|muc-luc|ban-quyen|bia)(?:$|[-_/ .])", re.I,
)
DINH_DANG = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def slug(chu):
    chu = unicodedata.normalize("NFD", chu.casefold().replace("đ", "d"))
    chu = "".join(c for c in chu if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", chu).strip("-")


def ten_the(the):
    return the.rsplit("}", 1)[-1]


class EbookEpub:
    def __init__(self, tep):
        self.tep = tep

    def doc(self):
        with ZipFile(self.tep) as epub:
            container = ElementTree.fromstring(epub.read("META-INF/container.xml"))
            opf = next(x.get("full-path") for x in container.iter() if ten_the(x.tag) == "rootfile")
            goi = ElementTree.fromstring(epub.read(opf))
            meta = goi.find("{*}metadata")
            thong_tin = {k: self._gia_tri(meta, k) for k in ("title", "creator", "description", "publisher")}
            thong_tin["title"] = thong_tin["title"] or self.tep.stem
            muc = {x.get("id"): x for x in goi.findall("{*}manifest/{*}item")}
            cover = self._bia(epub, opf, meta, muc)
            trich = self._trich(epub, opf, goi, muc)
        return dict(thong_tin, the_loai=self.tep.parent.name, trich=trich), cover

    @staticmethod
    def _gia_tri(meta, key):
        if meta is None:
            return ""
        muc = [" ".join("".join(x.itertext()).split()) for x in meta if ten_the(x.tag) == key]
        return "; ".join(filter(None, muc)) if key == "creator" else next(filter(None, muc), "")

    @staticmethod
    def _duong_dan(opf, item):
        duong = unquote(urlsplit(item.get("href", "")).path)
        return posixpath.normpath(posixpath.join(posixpath.dirname(opf), duong))

    def _bia(self, epub, opf, meta, muc):
        ma = next((x.get("content") for x in (meta if meta is not None else ()) if x.get("name") == "cover"), None)
        cover = next((x for x in muc.values() if "cover-image" in x.get("properties", "").split()), None)
        if cover is None:
            cover = muc.get(ma)
        if cover is None:
            cover = next((x for x in muc.values() if "cover" in x.get("href", "").lower()
                          and x.get("media-type") in DINH_DANG), None)
        if cover is not None and cover.get("media-type") in DINH_DANG:
            return DINH_DANG[cover.get("media-type")], epub.read(self._duong_dan(opf, cover))
        return None

    def _trich(self, epub, opf, goi, muc):
        tu = []
        for ref in goi.findall("{*}spine/{*}itemref"):
            item = muc.get(ref.get("idref"))
            if item is None or ref.get("linear") == "no" or "nav" in item.get("properties", "").split():
                continue
            duong = self._duong_dan(opf, item)
            if BO_QUA.search(slug(PurePosixPath(duong).stem)):
                continue
            try:
                html = ElementTree.fromstring(epub.read(duong))
            except (ElementTree.ParseError, KeyError):
                continue
            body = next((x for x in html.iter() if ten_the(x.tag) == "body"), html)
            dau_muc = next((" ".join(x.itertext()).strip() for x in body.iter()
                            if ten_the(x.tag) in {"h1", "h2", "h3", "p"}), "")
            if len(dau_muc.split()) < 15 and BO_QUA.search(slug(dau_muc)):
                continue
            for text in self._van_ban(body):
                tu.extend(text.split())
                if len(tu) >= 1500:
                    return " ".join(tu[:1500])
        return " ".join(tu)

    def _van_ban(self, nut):
        loai = " ".join(v for k, v in nut.attrib.items() if ten_the(k) in {"type", "role", "id"})
        if BO_QUA.search(slug(loai)):
            return
        if ten_the(nut.tag) in {"p", "h1", "h2", "h3", "li", "blockquote"}:
            text = "".join(nut.itertext()).strip()
            if not (BO_QUA.search(slug(text)) and len(text.split()) < 15):
                yield text
            return
        for con in nut:
            yield from self._van_ban(con)


def chon_sach(sach):
    xep = sorted(sach, key=lambda s: (not s["co_bia"], not bool(s["description"]), slug(s["title"])))
    nhom = {ten: [s for s in xep if s["the_loai"] == ten] for ten in DANH_MUC}
    chon = [s for ds in nhom.values() for s in ds[:2]]
    them = [s for ten in ("Kinh Dị - Trinh Thám", "Triết Học - Tâm Lý Học") for s in nhom[ten][2:]]
    return chon + them[:max(0, 20 - len(chon))]


def nen_bia(nguon):
    with Image.open(nguon) as anh:
        anh = ImageOps.exif_transpose(anh).convert("RGBA")
        if anh.width > 600:
            cao = max(1, round(anh.height * 600 / anh.width))
            anh = anh.resize((600, cao), Image.Resampling.LANCZOS)
        nen = Image.new("RGB", anh.size, "white")
        nen.paste(anh, mask=anh.getchannel("A"))
        bo_dem = BytesIO()
        nen.save(bo_dem, format="JPEG", quality=82, optimize=True)
        return bo_dem.getvalue()


def chay(nguon, dich, thu_muc_bia):
    ds = []
    for tep in sorted(nguon.rglob("*.epub")):
        if tep.parent.name not in DANH_MUC:
            continue
        try:
            sach, bia = EbookEpub(tep).doc()
        except (ValueError, KeyError, ElementTree.ParseError, StopIteration) as exc:
            print(f"Bỏ qua EPUB {tep.name}: {type(exc).__name__}")
            continue
        ds.append(dict(sach, co_bia=bia is not None, _bia=bia))
    ket_qua = chon_sach(ds)
    if len(ket_qua) != 20:
        raise ValueError(f"Cần 20 sách, đã chọn {len(ket_qua)} từ {len(ds)} EPUB đọc được.")
    thu_muc_bia.mkdir(parents=True, exist_ok=True)
    for sach in ket_qua:
        bia = sach.pop("_bia")
        ten = slug(sach["title"]) or "sach"
        if bia:
            _, noi_dung = bia
            tep_bia = thu_muc_bia / (ten + ".jpg")
            tep_bia.write_bytes(nen_bia(BytesIO(noi_dung)))
            sach["anh_bia"] = f"/bia-ebook/{tep_bia.name}"
        else:
            sach["anh_bia"] = None
        sach["danh_muc"] = DANH_MUC[sach["the_loai"]][1]
    dich.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"Đã chọn {len(ket_qua)} sách từ {len(ds)} EPUB.")


def cap_nhat_danh_muc(tep_trich, tep_mau):
    moi = json.loads(tep_trich.read_text(encoding="utf8"))
    mau = json.loads(tep_mau.read_text(encoding="utf8"))
    slug_da_co = {muc["duong_dan"] for muc in mau["danh_muc"]}
    for ten, ma in DANH_MUC.values():
        if ma not in slug_da_co:
            mau["danh_muc"].append(dict(ten=ten, duong_dan=ma))
            slug_da_co.add(ma)

    sach_cu = [sach for sach in mau["sach"] if not sach.get("ebook_mau")]
    for index, sach in enumerate(moi):
        # Giá bìa thử tăng theo bậc 10.000 đ, giảm 10.000 đ; tồn luân phiên 8, 10 và 12.
        gia_bia = 89000 + index % 7 * 10000
        mo_ta = " ".join(re.sub(r"<[^>]+>", " ", unescape(sach["description"])).split())
        if len(mo_ta) > 500:
            mo_ta = mo_ta[:500].rsplit(" ", 1)[0] + "…"
        sach_cu.append(dict(
            tieu_de=sach["title"], tac_gia=sach["creator"] or "Chưa rõ",
            nha_xuat_ban=sach["publisher"] or None, nam_xuat_ban=None, so_trang=None,
            gia=gia_bia - 10000, gia_bia=gia_bia, ton_kho=8 + 2 * (index % 3),
            mo_ta=mo_ta, danh_muc=sach["danh_muc"], mau_bia="#2b4c7e",
            anh_bia=sach["anh_bia"], ebook_mau=True,
        ))
    mau["sach"] = sach_cu
    tep_mau.write_text(json.dumps(mau, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nguon", type=Path, default=Path("du_lieu/ebook_nguon"))
    p.add_argument("--dich", type=Path, default=Path("du_lieu/ebook_trich.json"))
    p.add_argument("--bia", type=Path, default=Path("du_lieu/bia"))
    p.add_argument("--cap-nhat-mau", type=Path)
    a = p.parse_args()
    chay(a.nguon, a.dich, a.bia)
    if a.cap_nhat_mau:
        cap_nhat_danh_muc(a.dich, a.cap_nhat_mau)


if __name__ == "__main__":
    main()
