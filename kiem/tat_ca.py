"""Chạy mọi kiểm bằng máy của dự án (THIET_KE.md mục 6).

Chạy trong thư mục gốc của dự án:  python kiem/tat_ca.py [--tich-hop]
Kiểm nào chưa có file (phần đó chưa được viết) thì in "chưa có" và không tính là đạt hay lỗi.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MOI_TRUONG = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def chay(ten: str, lenh: list[str], can_file: str | None = None, tich_hop: bool = False) -> bool | None:
    if can_file and not os.path.exists(os.path.join(GOC, can_file)):
        print(f"[{'LỖI: thiếu' if tich_hop else 'chưa có'}] {ten} ({can_file})")
        return False if tich_hop else None
    kq = subprocess.run(lenh, cwd=GOC, capture_output=True, text=True, encoding="utf-8", errors="replace", env=MOI_TRUONG)
    dat = kq.returncode == 0
    print(f"[{'đạt' if dat else 'LỖI'}] {ten}")
    if not dat:
        print("\n".join("    " + d for d in (kq.stdout + kq.stderr).strip().splitlines()[-25:]))
    return dat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tich-hop", action="store_true",
                    help="chế độ đầy đủ: thiếu kiểm nào là LỖI, test tích hợp bắt buộc chạy")
    a = ap.parse_args()
    if a.tich_hop:
        MOI_TRUONG["NHA_SACH_TICH_HOP"] = "1"
    py, th = sys.executable, a.tich_hop
    thieu = [m for m in ("flask", "segno") if subprocess.run([py, "-c", f"import {m}"], capture_output=True, env=MOI_TRUONG).returncode]
    if thieu:
        print(f"[LỖI MÔI TRƯỜNG] Python này ({py}) chưa cài: {', '.join(thieu)}. "
              "Chạy bằng .venv của dự án (.venv\\Scripts\\python.exe kiem/tat_ca.py) "
              "hoặc cài: python -m pip install -r requirements.txt")
        return 1
    ket_qua = [
        chay("test Python (nghiệp vụ, kiến trúc, hợp đồng, dữ liệu, tích hợp)", [py, "-m", "unittest", "discover", "-s", "tests", "-t", "."], "tests", th),
        chay("template dựng được (xem_truoc.py)", [py, "xem_truoc.py"], "xem_truoc.py", th),
        chay("font tiếng Việt", [py, "kiem_giao_dien/font.py"], "kiem_giao_dien/font.py", th),
        chay("tràn ngang", [py, "kiem_giao_dien/tran_ngang.py"], "kiem_giao_dien/tran_ngang.py", th),
        chay("tương phản màu WCAG", [py, "kiem_giao_dien/tuong_phan.py"], "kiem_giao_dien/tuong_phan.py", th),
        chay("vùng chạm 44px ở 390px", [py, "kiem_giao_dien/vung_cham.py"], "kiem_giao_dien/vung_cham.py", th),
        chay("token cỡ chữ và bo góc", [py, "kiem_giao_dien/token.py"], "kiem_giao_dien/token.py", th),
        chay("bố cục (ô tìm kiếm, cắt chữ)", [py, "kiem_giao_dien/bo_cuc.py"], "kiem_giao_dien/bo_cuc.py", th),
    ]
    co_loi = any(k is False for k in ket_qua)
    print("KẾT QUẢ:", "LỖI" if co_loi else ("đạt (đủ mọi kiểm)" if th else "đạt (các kiểm đang có)"))
    return 1 if co_loi else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
