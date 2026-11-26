"""Kiểm kích thước vùng chạm (>= 44px) ở màn hình điện thoại 390px cho mọi trang xem_truoc/*.html.

Dùng Edge headless + iframe 390px đo mọi `a.nut, button, input, select` đang hiển thị
(THIET_KE.md mục 7, V2-1). Thoát 0 khi mọi phần tử đạt >= 44px, thoát 1 khi có phần tử nhỏ hơn.
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
BE_RONG_DIEN_THOAI = 390
CAO_TOI_THIEU = 44.0
SAI_SO_PX = 0.2
SO_TRANG_MOI_LO = 6

DUONG_DAN_EDGE = [
    os.environ.get("EDGE_EXE", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def tim_edge() -> str:
    for duong_dan in DUONG_DAN_EDGE:
        if duong_dan and Path(duong_dan).is_file():
            return duong_dan
    raise FileNotFoundError("Khong tim thay msedge.exe de kiem vung cham.")


def tao_html_do(cac_ten_trang: list[str]) -> str:
    khung_iframe = []
    danh_sach = []
    for chi_so, ten in enumerate(cac_ten_trang):
        fid = f"p{chi_so}"
        danh_sach.append({"id": fid, "trang": ten})
        khung_iframe.append(
            f'<iframe id="{fid}" src="/xem_truoc/{ten}" width="{BE_RONG_DIEN_THOAI}" height="900"></iframe>'
        )

    cau_hinh_json = json.dumps(danh_sach, ensure_ascii=False)
    nguong = CAO_TOI_THIEU - SAI_SO_PX
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{margin:0;padding:0}iframe{border:0;display:block}</style></head><body>"
        + "".join(khung_iframe)
        + "<pre id='ket-qua-vung-cham'></pre>"
        + "<script>"
        f"const DS = {cau_hinh_json};"
        f"const NGUONG = {nguong};"
        "function moTaPhanTu(el) {"
        "  const tag = el.tagName.toLowerCase();"
        "  const id = el.id ? '#' + el.id : '';"
        "  const cls = typeof el.className === 'string' && el.className.trim()"
        "    ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.')"
        "    : '';"
        "  const nhan = (el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || '').trim().replace(/\\s+/g, ' ').slice(0, 32);"
        "  return tag + id + cls + (nhan ? ' \"' + nhan + '\"' : '');"
        "}"
        "function dangHienThi(el, win) {"
        "  if (el.tagName === 'INPUT' && (el.type || '').toLowerCase() === 'hidden') return false;"
        "  const cs = win.getComputedStyle(el);"
        "  if (cs.display === 'none' || cs.visibility === 'hidden') return false;"
        "  let p = el.parentElement;"
        "  while (p) {"
        "    const pcs = win.getComputedStyle(p);"
        "    if (pcs.display === 'none' || pcs.visibility === 'hidden') return false;"
        "    if (p.tagName === 'DETAILS' && !p.open && el.tagName !== 'SUMMARY' && !el.closest('summary')) return false;"
        "    p = p.parentElement;"
        "  }"
        "  const r = el.getBoundingClientRect();"
        "  return r.width > 0 && r.height > 0;"
        "}"
        "function chieuCaoVungCham(el, doc) {"
        "  const r = el.getBoundingClientRect();"
        "  if (el.tagName === 'INPUT') {"
        "    const kieu = (el.type || '').toLowerCase();"
        "    if (kieu === 'radio' || kieu === 'checkbox') {"
        "      let lbl = el.closest('label');"
        "      if (!lbl && el.id) lbl = doc.querySelector('label[for=\"' + el.id + '\"]');"
        "      if (lbl) {"
        "        const lr = lbl.getBoundingClientRect();"
        "        return {w: Math.max(r.width, lr.width), h: Math.max(r.height, lr.height)};"
        "      }"
        "    }"
        "  }"
        "  return {w: r.width, h: r.height};"
        "}"
        "window.addEventListener('load', () => {"
        "  const kq = DS.map(m => {"
        "    const f = document.getElementById(m.id);"
        "    const doc = f.contentDocument;"
        "    const win = f.contentWindow;"
        "    const phanTu = Array.from(doc.querySelectorAll('a.nut, a.nut-gio, a.tai-khoan-the, a.phan-trang__nut, a.nut-sap-xep, a.chip-gia, a.menu-ql__muc, a.ql-xem-cua-hang, a.nut-in, a.dai-tien-ich__tra-cuu, a.menu-danh-muc__link, a.xem-them, button, input, select'));"
        "    let tong = 0;"
        "    const loi = [];"
        "    for (const el of phanTu) {"
        "      if (!dangHienThi(el, win)) continue;"
        "      tong += 1;"
        "      const kt = chieuCaoVungCham(el, doc);"
        "      if (kt.h < NGUONG) {"
        "        loi.push({moTa: moTaPhanTu(el), rong: Math.round(kt.w * 10) / 10, cao: Math.round(kt.h * 10) / 10});"
        "      }"
        "    }"
        "    return {trang: m.trang, tong, loi};"
        "  });"
        "  document.getElementById('ket-qua-vung-cham').textContent = 'KET_QUA_VC:' + JSON.stringify(kq);"
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
        lo_map[f"/__vc_{i}"] = tao_html_do(nhom)

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
    with tempfile.TemporaryDirectory(prefix="edge_vung_cham_") as thu_muc_ho_so:
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
                        "--window-size=600,1000",
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
                    m = re.search(r"KET_QUA_VC:(\[.*?\])</pre>", tien_trinh.stdout, re.S)
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
    tong_phan_tu = sum(m["tong"] for m in ket_qua)
    cac_loi = [(m["trang"], item) for m in ket_qua for item in m["loi"]]

    if cac_loi:
        print(f"LOI vung cham (< {int(CAO_TOI_THIEU)}px o {BE_RONG_DIEN_THOAI}px):")
        for trang, item in cac_loi:
            print(
                f"  xem_truoc/{trang} @ {BE_RONG_DIEN_THOAI}px: "
                f"{item['moTa']} -> {item['rong']}x{item['cao']}px (< {int(CAO_TOI_THIEU)}px)"
            )
        return 1

    print(
        f"DAT kiem vung cham: {len(cac_trang)} trang @ {BE_RONG_DIEN_THOAI}px, "
        f"{tong_phan_tu} dieu khien va lien ket chinh deu cao >= {int(CAO_TOI_THIEU)}px."
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
