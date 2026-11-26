"""Kiểm chuẩn hóa token cỡ chữ (--c-*) và bo góc (--bo-*) trong static/css/giao_dien.css.

Đếm mọi khai báo `font-size` và `border-radius` viết thẳng (không dùng `var(...)`),
loại trừ các ngoại lệ có chủ đích:
- khối định nghĩa `:root` (chứa biến `--c-*`, `--bo-*`)
- `html { font-size: 16px; }` (gốc tính rem)
- `font-size: inherit`
- `border-radius: 0` (tắt bo góc)

Ngưỡng cho phép:
- NGUONG_FONT_SIZE = 0
- NGUONG_BORDER_RADIUS = 0

Thoát mã 0 khi đạt ngưỡng và mọi token `--c-*` / `--bo-*` được dùng đều tồn tại trong `:root`;
thoát mã 1 khi vượt ngưỡng hoặc dùng token chưa định nghĩa.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


GOC = Path(__file__).resolve().parent.parent
TEP_CSS = GOC / "static" / "css" / "giao_dien.css"

# Ngưỡng tối đa cho số khai báo viết thẳng (không dùng var(...))
NGUONG_FONT_SIZE = 0
NGUONG_BORDER_RADIUS = 0


def bo_chu_thich_giu_dong(css: str) -> str:
    """Xóa chú thích /* ... */ nhưng giữ nguyên số dòng để báo đúng vị trí."""
    def thay(m: re.Match[str]) -> str:
        return "\n" * m.group(0).count("\n")

    return re.sub(r"/\*.*?\*/", thay, css, flags=re.S)


def trich_token_root(css_sach: str) -> tuple[dict[str, str], dict[str, str]]:
    """Lấy các token --c-* và --bo-* trong mọi khối :root."""
    token_chu: dict[str, str] = {}
    token_bo: dict[str, str] = {}
    for m in re.finditer(r":root\s*\{([^}]*)\}", css_sach, flags=re.S):
        for ten, gia_tri in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
            gt = " ".join(gia_tri.split())
            if ten.startswith("--c-"):
                token_chu[ten] = gt
            elif ten.startswith("--bo-"):
                token_bo[ten] = gt
    return token_chu, token_bo


def gia_tri_dung_token(gia_tri: str, tien_to: str) -> tuple[bool, list[str]]:
    """Kiểm tra giá trị có hoàn toàn dùng var(--...) (kèm tùy chọn số 0) hay không."""
    gt = " ".join(gia_tri.split())
    cac_var = re.findall(r"var\(\s*(--[a-z0-9-]+)\s*\)", gt)
    if not cac_var:
        return False, []
    phan_du = re.sub(r"var\(\s*--[a-z0-9-]+\s*\)", "", gt).strip()
    if phan_du:
        for phan in phan_du.split():
            if not re.fullmatch(r"0(?:px|rem|em|%)?", phan):
                return False, cac_var
    dung_tien_to = all(v.startswith(tien_to) for v in cac_var)
    return dung_tien_to, cac_var


def duyet_khai_bao(css_sach: str) -> list[tuple[int, str, str, str]]:
    """Trích mọi khai báo (dong, bo_chon, thuoc_tinh, gia_tri) ngoài khối :root.

    Hoạt động đúng với cả quy tắc nhiều dòng lẫn một dòng (vd: `.a { font-size: 15px; }`).
    """
    ket_qua: list[tuple[int, str, str, str]] = []
    # Duyệt từng khối quy tắc lá `{ ... }` (không chứa `{` lồng nhau)
    for m in re.finditer(r"([^{};]+)\{([^{}]*)\}", css_sach, flags=re.S):
        bo_chon = " ".join(m.group(1).split())
        if bo_chon == ":root":
            continue
        than = m.group(2)
        vi_tri_than = m.start(2)
        for dm in re.finditer(
            r"(?:^|[;\s])(font-size|border-radius)\s*:\s*([^;]+?)\s*(?:;|$)",
            than,
            flags=re.S,
        ):
            thuoc_tinh = dm.group(1)
            gia_tri = " ".join(dm.group(2).split())
            vi_tri = vi_tri_than + dm.start(1)
            so_dong = css_sach.count("\n", 0, vi_tri) + 1
            ket_qua.append((so_dong, bo_chon, thuoc_tinh, gia_tri))
    return ket_qua


def kiem_tra_css(duong_dan: Path) -> int:
    css_goc = duong_dan.read_text(encoding="utf-8")
    css_sach = bo_chu_thich_giu_dong(css_goc)
    token_chu, token_bo = trich_token_root(css_sach)

    dem_fs_token = 0
    dem_br_token = 0
    loi_fs: list[tuple[int, str]] = []
    loi_br: list[tuple[int, str]] = []
    bien_thieu: list[tuple[int, str]] = []

    for so_dong, bo_chon, thuoc_tinh, gt in duyet_khai_bao(css_sach):
        if thuoc_tinh == "font-size":
            if gt == "inherit" or (bo_chon == "html" and gt == "16px"):
                continue
            ok, cac_var = gia_tri_dung_token(gt, "--c-")
            if ok:
                dem_fs_token += 1
                for v in cac_var:
                    if v not in token_chu:
                        bien_thieu.append((so_dong, v))
            else:
                loi_fs.append((so_dong, f"font-size: {gt};"))
        elif thuoc_tinh == "border-radius":
            if re.fullmatch(r"(?:0(?:px|rem|em|%)?\s*)+", gt):
                continue
            ok, cac_var = gia_tri_dung_token(gt, "--bo-")
            if ok:
                dem_br_token += 1
                for v in cac_var:
                    if v not in token_bo:
                        bien_thieu.append((so_dong, v))
            else:
                loi_br.append((so_dong, f"border-radius: {gt};"))

    ten_tuong_doi = duong_dan.relative_to(GOC).as_posix()
    print(
        f"Token trong :root: {len(token_chu)} bac chu (--c-*), "
        f"{len(token_bo)} bac bo goc (--bo-*)"
    )
    print(
        f"font-size: {dem_fs_token} dung var(--c-*), "
        f"{len(loi_fs)} viet thang (nguong <= {NGUONG_FONT_SIZE})"
    )
    print(
        f"border-radius: {dem_br_token} dung var(--bo-*), "
        f"{len(loi_br)} viet thang (nguong <= {NGUONG_BORDER_RADIUS})"
    )

    if bien_thieu:
        print("LOI token chua dinh nghia trong :root:")
        for dong_so, ten_bien in bien_thieu:
            print(f"  {ten_tuong_doi}:{dong_so}: {ten_bien}")

    if len(loi_fs) > NGUONG_FONT_SIZE:
        print(
            f"LOI vuot nguong font-size viet thang ({len(loi_fs)} > {NGUONG_FONT_SIZE}):"
        )
        for dong_so, noi_dung in loi_fs:
            print(f"  {ten_tuong_doi}:{dong_so}: {noi_dung}")

    if len(loi_br) > NGUONG_BORDER_RADIUS:
        print(
            f"LOI vuot nguong border-radius viet thang ({len(loi_br)} > {NGUONG_BORDER_RADIUS}):"
        )
        for dong_so, noi_dung in loi_br:
            print(f"  {ten_tuong_doi}:{dong_so}: {noi_dung}")

    if (
        len(loi_fs) > NGUONG_FONT_SIZE
        or len(loi_br) > NGUONG_BORDER_RADIUS
        or bien_thieu
        or not token_chu
        or not token_bo
    ):
        return 1

    print("DAT: tat ca font-size va border-radius deu dung token chuan.")
    return 0


def main() -> int:
    if not TEP_CSS.is_file():
        print(f"Khong tim thay {TEP_CSS}", file=sys.stderr)
        return 1
    return kiem_tra_css(TEP_CSS)


if __name__ == "__main__":
    raise SystemExit(main())
