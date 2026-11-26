"""Kiểm tràn ngang cho mọi trang trong xem_truoc/ ở các bề rộng 360, 400, 768, 1440 px.

Dùng Edge headless mở trang đo chứa các iframe đúng bề rộng mục tiêu (tránh giới hạn
chiều rộng cửa sổ tối thiểu ~500px của Windows khi chạy --headless=new), đọc kết quả
`document.documentElement.scrollWidth <= window.innerWidth` qua `--dump-dom`.
Thoát 0 nếu mọi trang ở mọi bề rộng đều đạt, thoát 1 nếu có trang tràn ngang hoặc lỗi đo.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


GOC = Path(__file__).resolve().parent.parent
THU_MUC_XEM_TRUOC = GOC / "xem_truoc"
CAC_BE_RONG = (360, 400, 768, 1440)
SO_TRANG_MOI_LO = 4

DUONG_DAN_EDGE = [
    os.environ.get("EDGE_EXE", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def tim_edge() -> str:
    for duong_dan in DUONG_DAN_EDGE:
        if duong_dan and Path(duong_dan).is_file():
            return duong_dan
    raise FileNotFoundError("Khong tim thay msedge.exe de kiem tran ngang.")


def tao_html_do(cac_ten_trang: list[str]) -> str:
    # Mỗi iframe đặt đúng bề rộng cần đo; sự kiện window.load của trang cha chỉ bắn
    # sau khi toàn bộ iframe tĩnh và CSS bên trong tải xong (không cần time.sleep).
    khung_iframe = []
    danh_sach_id = []
    for chi_so, ten in enumerate(cac_ten_trang):
        for w in CAC_BE_RONG:
            fid = f"p{chi_so}_{w}"
            danh_sach_id.append({"id": fid, "trang": ten, "rong": w})
            khung_iframe.append(
                f'<iframe id="{fid}" src="/xem_truoc/{ten}" width="{w}" height="900"></iframe>'
            )

    cau_hinh_json = json.dumps(danh_sach_id, ensure_ascii=False)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{margin:0;padding:0}iframe{border:0;display:block}</style></head><body>"
        + "".join(khung_iframe)
        + "<pre id='ket-qua-do'></pre>"
        + "<script>"
        f"const DS = {cau_hinh_json};"
        "window.addEventListener('load', () => {"
        "  const kq = DS.map(m => {"
        "    const f = document.getElementById(m.id);"
        "    const doc = f.contentDocument;"
        "    const win = f.contentWindow;"
        "    const sw = doc.documentElement.scrollWidth;"
        "    const iw = win.innerWidth;"
        "    return {trang: m.trang, rong: m.rong, scrollWidth: sw, innerWidth: iw, dat: sw <= iw};"
        "  });"
        "  document.getElementById('ket-qua-do').textContent = 'KET_QUA_DO:' + JSON.stringify(kq);"
        "});"
        "</script></body></html>"
    )


class MayChuDaLuong(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


def chay_do(cac_trang: list[str]) -> list[dict]:
    edge = tim_edge()
    lo_map: dict[str, str] = {}
    for i in range(0, len(cac_trang), SO_TRANG_MOI_LO):
        nhom = cac_trang[i : i + SO_TRANG_MOI_LO]
        lo_map[f"/__do_{i}"] = tao_html_do(nhom)

    class TrinhPhucVu(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(GOC), **kwargs)

        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self) -> None:
            duong = self.path.split("?", 1)[0]
            if duong == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if duong in lo_map:
                du_lieu = lo_map[duong].encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(du_lieu)))
                self.end_headers()
                self.wfile.write(du_lieu)
                return
            super().do_GET()

    ket_qua: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="edge_tran_ngang_") as thu_muc_ho_so:
        with MayChuDaLuong(("127.0.0.1", 0), TrinhPhucVu) as may_chu:
            cong = may_chu.server_address[1]
            luong = threading.Thread(target=may_chu.serve_forever, daemon=True)
            luong.start()
            try:
                for chi_so, duong in enumerate(lo_map):
                    ho_so_lo = Path(thu_muc_ho_so) / f"lo_{chi_so}"
                    lenh = [
                        edge,
                        "--headless=new",
                        "--disable-gpu",
                        "--no-sandbox",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-background-networking",
                        "--disable-sync",
                        "--hide-scrollbars",
                        f"--user-data-dir={ho_so_lo}",
                        "--dump-dom",
                        "--window-size=1520,1000",
                        f"http://127.0.0.1:{cong}{duong}",
                    ]
                    tien_trinh = subprocess.run(
                        lenh,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=90,
                    )
                    m = re.search(r"KET_QUA_DO:(\[.*?\])</pre>", tien_trinh.stdout, re.S)
                    if not m:
                        raise RuntimeError(
                            f"Khong doc duoc ket qua do tai {duong} (rc={tien_trinh.returncode})"
                        )
                    ket_qua.extend(json.loads(m.group(1)))
            finally:
                may_chu.shutdown()

    return ket_qua


def main() -> int:
    if not THU_MUC_XEM_TRUOC.exists():
        print("LOI: Chua co thu muc xem_truoc/. Hay chay xem_truoc.py truoc.", file=sys.stderr)
        return 1

    cac_trang = sorted(p.name for p in THU_MUC_XEM_TRUOC.glob("*.html") if p.is_file())
    if not cac_trang:
        print("LOI: Khong co tep HTML nao trong xem_truoc/.", file=sys.stderr)
        return 1

    ket_qua = chay_do(cac_trang)
    cac_loi = [m for m in ket_qua if not m["dat"]]

    if cac_loi:
        print("LOI tran ngang:")
        for m in cac_loi:
            print(
                f"  xem_truoc/{m['trang']} @ {m['rong']}px: "
                f"scrollWidth={m['scrollWidth']} > innerWidth={m['innerWidth']}"
            )
        return 1

    print(
        f"DAT kiem tran ngang: {len(cac_trang)} trang x {len(CAC_BE_RONG)} be rong "
        f"{list(CAC_BE_RONG)} ({len(ket_qua)} ca deu scrollWidth <= innerWidth)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
