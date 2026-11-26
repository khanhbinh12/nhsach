"""Nhập nháp review từ JSON hoặc Markdown vào SQLite."""
import argparse
import json
from pathlib import Path
import re
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nha_sach.dich_vu import tao_dich_vu
from nha_sach.loi import LoiNghiepVu


def doc_markdown(noi_dung):
    # Mỗi mục bắt đầu bằng ## tiêu đề, rồi Sách hoặc Mã sách và Tác giả (tùy chọn).
    ds = []
    for khoi in re.split(r"(?m)^##\s+", noi_dung)[1:]:
        dong = khoi.splitlines()
        bai = {"tieu_de": dong.pop(0).strip(), "tac_gia_review": "Nhà Sách Tri Thức"}
        while dong:
            match = re.match(r"^(Mã sách|Sách|Tác giả):\s*(.+)$", dong[0].strip())
            if match is None:
                break
            kieu, gia_tri = match.groups()
            ten = {"Mã sách": "ma_sach", "Sách": "tieu_de_sach", "Tác giả": "tac_gia_review"}[kieu]
            bai[ten] = int(gia_tri) if ten == "ma_sach" else gia_tri.strip()
            dong.pop(0)
        bai["noi_dung"] = "\n".join(dong).strip()
        ds.append(bai)
    return ds


def doc_tep(tep):
    noi_dung = tep.read_text(encoding="utf-8-sig")
    if tep.suffix.lower() in {".md", ".markdown"}:
        du_lieu = doc_markdown(noi_dung)
    elif tep.suffix.lower() == ".json":
        du_lieu = json.loads(noi_dung)
        if isinstance(du_lieu, dict):
            du_lieu = du_lieu.get("reviews")
    else:
        raise ValueError("Chỉ nhận .json hoặc .md.")
    if not isinstance(du_lieu, list) or not du_lieu:
        raise ValueError("Tệp phải có ít nhất một review.")
    for bai in du_lieu:
        if not isinstance(bai, dict):
            raise ValueError("Mỗi review phải là một đối tượng.")
        bai.setdefault("tac_gia_review", "Nhà Sách Tri Thức")
        for ten in ("tieu_de", "noi_dung", "tac_gia_review"):
            if not isinstance(bai.get(ten), str) or not bai[ten].strip():
                raise ValueError(f"Review thiếu {ten}.")
        if "ma_sach" in bai:
            if type(bai["ma_sach"]) is not int or bai["ma_sach"] < 1:
                raise ValueError("Mã sách phải là số nguyên dương.")
        elif not isinstance(bai.get("tieu_de_sach"), str) or not bai["tieu_de_sach"].strip():
            raise ValueError("Review thiếu mã sách hoặc tên sách.")
        elif "tieu_de_sach" in bai:
            bai["tieu_de_sach"] = bai["tieu_de_sach"].strip()
    return du_lieu


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tep", type=Path, help="JSON: ma_sach hoặc tieu_de_sach, tieu_de, noi_dung, tac_gia_review.")
    p.add_argument("--db", type=Path, required=True, help="CSDL SQLite đã nạp sách.")
    a = p.parse_args()
    if not a.db.is_file():
        p.error("Không tìm thấy CSDL.")
    try:
        du_lieu = doc_tep(a.tep)
        _, quan_ly = tao_dich_vu(a.db)
        ket_qua = quan_ly.nhap_review(du_lieu)
    except (OSError, ValueError, LoiNghiepVu) as exc:
        p.error(str(exc))
    print(f"Đã nhập {len(ket_qua)} bài review nháp.")


if __name__ == "__main__":
    main()
