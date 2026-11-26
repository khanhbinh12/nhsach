"""Kiểm tỉ lệ tương phản màu WCAG 2.1 từ các biến màu trong static/css/giao_dien.css (THIET_KE.md mục 7, V2-1).

Chữ thường yêu cầu >= 4.5:1; viền điều khiển và biểu tượng yêu cầu >= 3.0:1.
Thoát 0 khi mọi cặp màu đều đạt, thoát 1 khi có cặp màu không đạt hoặc thiếu token.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


GOC = Path(__file__).resolve().parent.parent
TEP_CSS = GOC / "static" / "css" / "giao_dien.css"

RE_ROOT = re.compile(r":root\s*\{([^}]*)\}", re.S)
RE_TOKEN = re.compile(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;")

# (ten_cap, mau_truoc, mau_nen, nguong_wcag)
CAC_CAP_KIEM: list[tuple[str, str, str, float]] = [
    # Chữ chính, chữ phụ, chữ nhạt >= 4.5:1 trên trắng, bề mặt nhẹ và nền kem
    ("Chữ chính trên trắng", "--chu", "--be-mat", 4.5),
    ("Chữ chính trên bề mặt nhẹ", "--chu", "--be-mat-nhe", 4.5),
    ("Chữ chính trên nền trang", "--chu", "--nen", 4.5),
    ("Chữ phụ trên trắng", "--chu-phu", "--be-mat", 4.5),
    ("Chữ phụ trên bề mặt nhẹ", "--chu-phu", "--be-mat-nhe", 4.5),
    ("Chữ phụ trên nền trang", "--chu-phu", "--nen", 4.5),
    ("Chữ nhạt trên trắng", "--chu-nhat", "--be-mat", 4.5),
    ("Chữ nhạt trên bề mặt nhẹ", "--chu-nhat", "--be-mat-nhe", 4.5),
    ("Chữ nhạt trên nền trang", "--chu-nhat", "--nen", 4.5),
    # Màu nhấn & chữ trắng trên nền màu nhấn / nền tối
    ("Màu nhấn trên trắng", "--nhan", "--be-mat", 4.5),
    ("Màu nhấn trên nền nhấn nhạt", "--nhan", "--nhan-nhat", 4.5),
    ("Chữ trắng trên nút chính", "#ffffff", "--nhan", 4.5),
    ("Chữ trắng trên nút chính hover", "#ffffff", "--nhan-dam", 4.5),
    ("Chữ trắng trên dải tiện ích tối", "#ffffff", "--chu", 4.5),
    # Trạng thái tốt / lỗi / cảnh báo >= 4.5:1
    ("Chữ trạng thái tốt trên trắng", "--tot", "--be-mat", 4.5),
    ("Chữ trạng thái tốt trên nền tốt", "--tot", "--tot-nen", 4.5),
    ("Chữ trạng thái lỗi trên trắng", "--loi", "--be-mat", 4.5),
    ("Chữ trạng thái lỗi trên nền lỗi", "--loi", "--loi-nen", 4.5),
    ("Chữ cảnh báo trên trắng", "--canh-bao", "--be-mat", 4.5),
    ("Chữ cảnh báo trên nền cảnh báo", "--canh-bao", "--canh-bao-nen", 4.5),
    # Viền ô nhập & phân trang >= 3.0:1 (WCAG 1.4.11)
    ("Viền điều khiển trên trắng", "--vien-dam", "--be-mat", 3.0),
    ("Viền điều khiển trên bề mặt nhẹ", "--vien-dam", "--be-mat-nhe", 3.0),
    ("Viền điều khiển trên nền trang", "--vien-dam", "--nen", 3.0),
    # Biểu tượng sao >= 3.0:1 (WCAG 1.4.11)
    ("Sao đánh giá trên trắng", "--sao", "--be-mat", 3.0),
    ("Sao đánh giá trên bề mặt nhẹ", "--sao", "--be-mat-nhe", 3.0),
    ("Sao đánh giá trên nền trang", "--sao", "--nen", 3.0),
]


def chuan_hex(mau: str) -> str:
    h = mau.strip().lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or not re.fullmatch(r"[0-9a-f]{6}", h):
        raise ValueError(f"Mã màu không hợp lệ: {mau}")
    return f"#{h}"


def do_sang_tuong_doi(mau_hex: str) -> float:
    h = chuan_hex(mau_hex).lstrip("#")
    kenh = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255.0
        kenh.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kenh[0] + 0.7152 * kenh[1] + 0.0722 * kenh[2]


def ti_le_tuong_phan(mau_a: str, mau_b: str) -> float:
    l1, l2 = sorted((do_sang_tuong_doi(mau_a), do_sang_tuong_doi(mau_b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def doc_token_mau(duong_dan: Path) -> dict[str, tuple[str, int]]:
    noi_dung = duong_dan.read_text(encoding="utf-8")
    m_root = RE_ROOT.search(noi_dung)
    if not m_root:
        raise RuntimeError(f"Không tìm thấy khối :root trong {duong_dan}")
    vi_tri_root = m_root.start(1)
    ket_qua: dict[str, tuple[str, int]] = {}
    for m in RE_TOKEN.finditer(m_root.group(1)):
        dong = noi_dung.count("\n", 0, vi_tri_root + m.start()) + 1
        ket_qua[m.group(1)] = (chuan_hex(m.group(2)), dong)
    return ket_qua


def giai_mau(gia_tri: str, tokens: dict[str, tuple[str, int]]) -> tuple[str, int | None]:
    if gia_tri.startswith("#"):
        return chuan_hex(gia_tri), None
    if gia_tri not in tokens:
        raise KeyError(f"Thiếu biến màu {gia_tri} trong :root")
    return tokens[gia_tri]


def main() -> int:
    if not TEP_CSS.is_file():
        print(f"LOI: Không tìm thấy {TEP_CSS}", file=sys.stderr)
        return 1

    tokens = doc_token_mau(TEP_CSS)
    rel = TEP_CSS.relative_to(GOC).as_posix()
    cac_loi: list[str] = []
    min_chu = (99.0, "")
    min_ui = (99.0, "")

    for ten, truoc, nen, nguong in CAC_CAP_KIEM:
        try:
            hex_truoc, dong_truoc = giai_mau(truoc, tokens)
            hex_nen, dong_nen = giai_mau(nen, tokens)
        except (KeyError, ValueError) as exc:
            cac_loi.append(f"{rel}: {ten}: {exc}")
            continue

        ti_le = ti_le_tuong_phan(hex_truoc, hex_nen)
        if nguong >= 4.5 and ti_le < min_chu[0]:
            min_chu = (ti_le, f"{truoc} ({hex_truoc}) / {nen} ({hex_nen})")
        elif nguong < 4.5 and ti_le < min_ui[0]:
            min_ui = (ti_le, f"{truoc} ({hex_truoc}) / {nen} ({hex_nen})")

        if ti_le < nguong:
            vi_tri = f"{rel}:{dong_truoc}" if dong_truoc else (f"{rel}:{dong_nen}" if dong_nen else rel)
            cac_loi.append(
                f"{vi_tri}: {ten} — {truoc} ({hex_truoc}) trên {nen} ({hex_nen}) "
                f"= {ti_le:.2f}:1 < {nguong:.1f}:1"
            )

    if cac_loi:
        print("LOI tuong phan mau WCAG:")
        for dong in cac_loi:
            print("  " + dong)
        return 1

    print(
        f"DAT kiem tuong phan WCAG ({len(CAC_CAP_KIEM)} cap mau trong {rel}; "
        f"chu thap nhat {min_chu[0]:.2f}:1 [{min_chu[1]}], "
        f"vien/bieu tuong thap nhat {min_ui[0]:.2f}:1 [{min_ui[1]}])."
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
