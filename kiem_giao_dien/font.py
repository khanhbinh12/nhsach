"""Kiểm font tiếng Việt trong static/css và templates (THIET_KE.md mục 5b).

Báo lỗi (exit 1) nếu bất kỳ khai báo `font-family` nào đặt font thiếu glyph tiếng Việt
(Georgia, Palatino, Garamond, ...) đứng TRƯỚC font hỗ trợ đầy đủ tiếng Việt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


GOC = Path(__file__).resolve().parent.parent

FONT_THIEU_VI = {
    "georgia",
    "palatino",
    "palatino linotype",
    "book antiqua",
    "garamond",
    "baskerville",
    "didot",
    "bodoni",
    "bodoni mt",
    "lucida calligraphy",
    "brush script mt",
}

FONT_DU_VI = {
    "be vietnam pro",
    "segoe ui",
    "times new roman",
    "arial",
    "roboto",
    "inter",
    "tahoma",
    "verdana",
    "helvetica",
    "helvetica neue",
    "consolas",
    "courier new",
    "noto sans",
    "noto serif",
    "open sans",
    "system-ui",
    "-apple-system",
    "blinkmacsystemfont",
}

RE_CSS_FONT = re.compile(r"font-family\s*:\s*([^;{}]+)(?:;|(?=\}))", re.IGNORECASE)
RE_CSS_VAR_FONT = re.compile(r"--font[a-z0-9_-]*\s*:\s*([^;{}]+)(?:;|(?=\}))", re.IGNORECASE)
RE_STYLE_ATTR = re.compile(r'style\s*=\s*(?:"([^"]+)"|\'([^\']+)\')', re.IGNORECASE)
RE_ATTR_FONT = re.compile(r'font-family\s*=\s*(?:"([^"]+)"|\'([^\']+)\')', re.IGNORECASE)


def tach_danh_sach_font(gia_tri: str) -> list[str]:
    cac_muc = []
    for phan in gia_tri.split(","):
        ten = phan.strip().strip("\"'").strip().lower()
        if ten and not ten.startswith("var("):
            cac_muc.append(ten)
    return cac_muc


def kiem_khai_bao(gia_tri: str) -> str | None:
    ds = tach_danh_sach_font(gia_tri)
    da_co_font_du_vi = False
    for ten in ds:
        if ten in FONT_DU_VI:
            da_co_font_du_vi = True
        elif ten in FONT_THIEU_VI and not da_co_font_du_vi:
            return f"font '{ten}' thiếu dấu tiếng Việt đứng trước font hỗ trợ tiếng Việt ({gia_tri.strip()})"
    return None


def so_dong(van_ban: str, vi_tri: int) -> int:
    return van_ban.count("\n", 0, vi_tri) + 1


def kiem_tep(duong_dan: Path) -> list[str]:
    noi_dung = duong_dan.read_text(encoding="utf-8")
    rel = duong_dan.relative_to(GOC).as_posix()
    loi: list[str] = []

    for m in RE_CSS_FONT.finditer(noi_dung):
        ly_do = kiem_khai_bao(m.group(1))
        if ly_do:
            loi.append(f"{rel}:{so_dong(noi_dung, m.start())}: {ly_do}")

    for m in RE_CSS_VAR_FONT.finditer(noi_dung):
        ly_do = kiem_khai_bao(m.group(1))
        if ly_do:
            loi.append(f"{rel}:{so_dong(noi_dung, m.start())}: {ly_do}")

    for m in RE_STYLE_ATTR.finditer(noi_dung):
        style_val = m.group(1) if m.group(1) is not None else m.group(2)
        for mf in re.finditer(r"font-family\s*:\s*([^;]+)", style_val, re.IGNORECASE):
            ly_do = kiem_khai_bao(mf.group(1))
            if ly_do:
                loi.append(f"{rel}:{so_dong(noi_dung, m.start())}: {ly_do}")

    for m in RE_ATTR_FONT.finditer(noi_dung):
        gia_tri = m.group(1) if m.group(1) is not None else m.group(2)
        ly_do = kiem_khai_bao(gia_tri)
        if ly_do:
            loi.append(f"{rel}:{so_dong(noi_dung, m.start())}: {ly_do}")

    return loi


def main() -> int:
    cac_tep: list[Path] = []
    for thu_muc, duoi in [(GOC / "static" / "css", "*.css"), (GOC / "templates", "*.html"), (GOC / "templates", "*.svg")]:
        if thu_muc.exists():
            cac_tep.extend(sorted(thu_muc.rglob(duoi)))

    tat_ca_loi: list[str] = []
    for tep in cac_tep:
        tat_ca_loi.extend(kiem_tep(tep))

    if tat_ca_loi:
        print("LOI font tieng Viet:")
        for dong in tat_ca_loi:
            print("  " + dong)
        return 1

    print(f"DAT kiem font tieng Viet ({len(cac_tep)} tep da kiem).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
