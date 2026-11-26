"""Kiểm bố cục giao diện trên Edge headless ở 390px và 1440px cho mọi trang xem_truoc/*.html.

Các kiểm tự động:
1. Ô tìm kiếm (`form.tim-kiem`, nếu trang có): phải hiển thị và nằm gọn trong 250px đầu trang
   (`top >= 0` và `bottom <= 250`).
2. Không phần tử chữ nào bị cắt hoặc ẩn ngoài ý muốn:
   - Không có phần tử chữ hiển thị có `scrollWidth > clientWidth` mà không khai báo
     `text-overflow: ellipsis` (loại trừ vùng cuộn ngang có chủ đích và `.sr-only`).
   - Không có phần tử chữ nào tràn vượt mép phải của khung chứa cắt ngang (`overflow-x: hidden/clip`
     hoặc `.thanh-ben-ql`) mà không có `text-overflow: ellipsis`.
   - Không có phần tử chữ không ẩn có chủ đích nào bị co về chiều rộng/cao 0 hoặc bị khung
     `overflow: hidden/clip` cắt mất hoàn toàn diện tích hiển thị.
3. Cấu trúc tiêu đề (heading) trên mỗi trang: đúng 1 thẻ `<h1>` và không nhảy bậc (`h1 -> h3`, ...).
4. Trang chi tiết sách (`chi_tiet.html`) ở 390×844px (#5): giá bán (`.chi-tiet__gia`) và nút mua
   (`.form-them-chi-tiet button[type="submit"]`) phải nằm trọn trong màn hình đầu (`bottom <= 844`).
5. Thanh điều hướng quản lý (`.menu-ql`) ở 390px (#6): không tràn ngang ẩn và mọi mục `.menu-ql__muc`
   phải hiển thị trọn trong bề rộng 390px.
6. Trang danh sách sách (`danh_sach.html`) ở 390px (#12): bộ lọc `.bo-loc-noi-dung` thu gọn mặc định
   và thẻ sách đầu tiên bắt đầu trong màn hình đầu (`top < 844`).
7. Ảnh bìa sách (`.bia img.bia__anh`): không méo — tỉ lệ hiển thị `width / height` khoảng 2:3
   (`0.667 ± 0.06`), dùng `object-fit: cover`, và ảnh trong màn hình đầu tải được (`naturalWidth > 0`).

Thoát mã 0 khi mọi trang đạt ở cả 390px và 1440px; thoát mã 1 kèm danh sách vị trí lỗi nếu không đạt.
"""

from __future__ import annotations

import html
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
CAC_BE_RONG = (390, 1440)
GIOI_HAN_TIM_KIEM_PX = 250.0
CAO_MAN_DAU_390_PX = 844.0
CAO_MAN_DAU_1440_PX = 900.0
NGUONG_BIA_TRANG_CHU_1440 = 6
NGUONG_BIA_TRANG_CHU_390 = 2
NGUONG_NUT_MUA_TRANG_CHU_390 = 1
SAI_SO_PX = 1.5
TI_LE_BIA_CHUAN = 2.0 / 3.0
SAI_SO_TI_LE_BIA = 0.06
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
    raise FileNotFoundError("Khong tim thay msedge.exe de kiem bo cuc.")


def tao_html_do(cac_ten_trang: list[str], be_rong: int) -> str:
    khung_iframe = []
    danh_sach = []
    for chi_so, ten in enumerate(cac_ten_trang):
        fid = f"p{chi_so}"
        danh_sach.append({"id": fid, "trang": ten})
        khung_iframe.append(
            f'<iframe id="{fid}" src="/xem_truoc/{ten}" width="{be_rong}" height="900"></iframe>'
        )

    cau_hinh_json = json.dumps(danh_sach, ensure_ascii=False)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{margin:0;padding:0}iframe{border:0;display:block}</style></head><body>"
        + "".join(khung_iframe)
        + "<pre id='ket-qua-bo-cuc'></pre>"
        + "<script>"
        f"const DS = {cau_hinh_json};"
        f"const BE_RONG = {be_rong};"
        f"const GIOI_HAN_TIM = {GIOI_HAN_TIM_KIEM_PX};"
        f"const CAO_MAN_DAU = {CAO_MAN_DAU_390_PX};"
        f"const CAO_MAN_DAU_1440 = {CAO_MAN_DAU_1440_PX};"
        f"const NGUONG_BIA_1440 = {NGUONG_BIA_TRANG_CHU_1440};"
        f"const NGUONG_BIA_390 = {NGUONG_BIA_TRANG_CHU_390};"
        f"const NGUONG_NUT_MUA_390 = {NGUONG_NUT_MUA_TRANG_CHU_390};"
        f"const SAI_SO = {SAI_SO_PX};"
        f"const TI_LE_BIA = {TI_LE_BIA_CHUAN};"
        f"const SAI_SO_TI_LE = {SAI_SO_TI_LE_BIA};"
        "const BO_QUA_THE = new Set(['SCRIPT','STYLE','NOSCRIPT','SVG','INPUT','TEXTAREA','SELECT','OPTION','IFRAME','IMG','BR','HR','META','LINK','TITLE']);"
        "const VUNG_CUON_CHU_DICH = '.menu-danh-muc, .bang-cuon, .khung-svg-bieu-do, .bang-so-lieu-bieu-do__cuon';"
        "function moTa(el) {"
        "  const tag = el.tagName.toLowerCase();"
        "  const id = el.id ? '#' + el.id : '';"
        "  const cls = typeof el.className === 'string' && el.className.trim()"
        "    ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.')"
        "    : '';"
        "  const txt = (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 36);"
        "  return tag + id + cls + (txt ? ' \"' + txt + '\"' : '');"
        "}"
        "function anCoChuDich(el, win, baoGomSrOnly) {"
        "  const cs = win.getComputedStyle(el);"
        "  if (cs.display === 'none' || cs.visibility === 'hidden') return true;"
        "  if (baoGomSrOnly && el.classList && (el.classList.contains('sr-only') || el.classList.contains('bo-qua-noi-dung'))) return true;"
        "  let p = el.parentElement;"
        "  while (p) {"
        "    const pcs = win.getComputedStyle(p);"
        "    if (pcs.display === 'none' || pcs.visibility === 'hidden') return true;"
        "    if (baoGomSrOnly && p.classList && p.classList.contains('sr-only')) return true;"
        "    if (p.tagName === 'DETAILS' && !p.open && el.tagName !== 'SUMMARY' && !el.closest('summary')) return true;"
        "    p = p.parentElement;"
        "  }"
        "  return false;"
        "}"
        "function dangHienThi(el, win) {"
        "  if (anCoChuDich(el, win, true)) return false;"
        "  const r = el.getBoundingClientRect();"
        "  return r.width > 0 && r.height > 0;"
        "}"
        "function coChuTrucTiep(el) {"
        "  for (const n of el.childNodes) {"
        "    if (n.nodeType === 3 && n.nodeValue && n.nodeValue.trim().length > 0) return true;"
        "  }"
        "  return false;"
        "}"
        "function coEllipsisHoacLineClamp(cs) {"
        "  if (cs.textOverflow === 'ellipsis') return true;"
        "  if (cs.webkitLineClamp && cs.webkitLineClamp !== 'none' && cs.webkitLineClamp !== '0') return true;"
        "  return false;"
        "}"
        "window.addEventListener('load', () => {"
        "  const kq = DS.map(m => {"
        "    const f = document.getElementById(m.id);"
        "    const doc = f.contentDocument;"
        "    const win = f.contentWindow;"
        "    const loi = [];"
        "    const tim = doc.querySelector('form.tim-kiem');"
        "    if (tim) {"
        "      const vis = dangHienThi(tim, win);"
        "      const r = tim.getBoundingClientRect();"
        "      if (!vis) {"
        "        loi.push({loai: 'tim_kiem', moTa: 'form.tim-kiem', chiTiet: 'bi an tren man ' + BE_RONG + 'px'});"
        "      } else if (r.top < -1 || r.bottom > GIOI_HAN_TIM + SAI_SO) {"
        "        loi.push({loai: 'tim_kiem', moTa: 'form.tim-kiem', chiTiet: 'top=' + Math.round(r.top) + 'px, bottom=' + Math.round(r.bottom) + 'px (vuot ' + GIOI_HAN_TIM + 'px)'});"
        "      }"
        "    }"
        "    const daBao = new Set();"
        "    for (const el of doc.body.querySelectorAll('*')) {"
        "      if (BO_QUA_THE.has(el.tagName)) continue;"
        "      if (el.closest('svg')) continue;"
        "      if (!coChuTrucTiep(el)) continue;"
        "      if (anCoChuDich(el, win, true)) continue;"
        "      const r = el.getBoundingClientRect();"
        "      if (r.width <= 0.5 || r.height <= 0.5) {"
        "        const key = 'zero:' + moTa(el);"
        "        if (!daBao.has(key)) {"
        "          daBao.add(key);"
        "          loi.push({loai: 'chu_bi_an', moTa: moTa(el), chiTiet: 'kich thuoc ' + Math.round(r.width) + 'x' + Math.round(r.height) + 'px (co chu nhung bi ep cao/rong 0)'});"
        "        }"
        "        continue;"
        "      }"
        "      if (el.closest(VUNG_CUON_CHU_DICH)) continue;"
        "      const cs = win.getComputedStyle(el);"
        "      const coEll = coEllipsisHoacLineClamp(cs);"
        "      if (!coEll && el.clientWidth > 0 && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll') {"
        "        if (el.scrollWidth > el.clientWidth + SAI_SO) {"
        "          const key = 'self:' + moTa(el);"
        "          if (!daBao.has(key)) {"
        "            daBao.add(key);"
        "            loi.push({loai: 'cat_chu', moTa: moTa(el), chiTiet: 'scrollWidth=' + Math.round(el.scrollWidth) + ' > clientWidth=' + Math.round(el.clientWidth) + ' (khong co text-overflow:ellipsis)'});"
        "          }"
        "        }"
        "      }"
        "      let p = el.parentElement;"
        "      let duocCatCoChuDich = coEll;"
        "      while (p && p !== doc.documentElement) {"
        "        const pcs = win.getComputedStyle(p);"
        "        const pr = p.getBoundingClientRect();"
        "        const catDoc = pcs.overflowY === 'hidden' || pcs.overflowY === 'clip';"
        "        const catNgang = pcs.overflowX === 'hidden' || pcs.overflowX === 'clip';"
        "        if (catDoc && (pr.height <= 0.5 || Math.min(r.bottom, pr.bottom) - Math.max(r.top, pr.top) <= 0.5)) {"
        "          const key = 'clip0y:' + moTa(el);"
        "          if (!daBao.has(key)) {"
        "            daBao.add(key);"
        "            loi.push({loai: 'chu_bi_an', moTa: moTa(el), chiTiet: 'bi khung ' + moTa(p) + ' cat an theo chieu doc (cao khung=' + Math.round(pr.height) + 'px)'});"
        "          }"
        "          break;"
        "        }"
        "        if (catNgang && (pr.width <= 0.5 || Math.min(r.right, pr.right) - Math.max(r.left, pr.left) <= 0.5)) {"
        "          const key = 'clip0x:' + moTa(el);"
        "          if (!daBao.has(key)) {"
        "            daBao.add(key);"
        "            loi.push({loai: 'chu_bi_an', moTa: moTa(el), chiTiet: 'bi khung ' + moTa(p) + ' cat an theo chieu ngang (rong khung=' + Math.round(pr.width) + 'px)'});"
        "          }"
        "          break;"
        "        }"
        "        if (coEllipsisHoacLineClamp(pcs)) { duocCatCoChuDich = true; break; }"
        "        if (p.matches && p.matches(VUNG_CUON_CHU_DICH)) { duocCatCoChuDich = true; break; }"
        "        const laKhungCat = catNgang || (p.classList && p.classList.contains('thanh-ben-ql'));"
        "        if (laKhungCat && !duocCatCoChuDich) {"
        "          if (r.right > pr.right + SAI_SO || r.left < pr.left - SAI_SO) {"
        "            const key = 'clip:' + moTa(el);"
        "            if (!daBao.has(key)) {"
        "              daBao.add(key);"
        "              loi.push({loai: 'cat_chu', moTa: moTa(el), chiTiet: 'tran khung ' + moTa(p) + ' (right=' + Math.round(r.right) + ' > ' + Math.round(pr.right) + ')'});"
        "            }"
        "            break;"
        "          }"
        "        }"
        "        p = p.parentElement;"
        "      }"
        "    }"
        "    const cacTieuDe = Array.from(doc.querySelectorAll('h1, h2, h3, h4, h5, h6')).filter(h => !anCoChuDich(h, win, false));"
        "    const soH1 = cacTieuDe.filter(h => h.tagName === 'H1').length;"
        "    if (soH1 !== 1) {"
        "      loi.push({loai: 'tieu_de', moTa: 'h1', chiTiet: 'trang co ' + soH1 + ' the h1 (can dung 1)'});"
        "    }"
        "    let bacTruoc = 0;"
        "    for (const h of cacTieuDe) {"
        "      const bac = parseInt(h.tagName.slice(1), 10);"
        "      if (bacTruoc > 0 && bac > bacTruoc + 1) {"
        "        loi.push({loai: 'tieu_de', moTa: moTa(h), chiTiet: 'nhay bac tu h' + bacTruoc + ' len h' + bac});"
        "      }"
        "      bacTruoc = bac;"
        "    }"
    "    if (m.trang === 'trang_chu.html') {"
        "      const gioiHanCao = BE_RONG === 1440 ? CAO_MAN_DAU_1440 : CAO_MAN_DAU;"
        "      let soBiaManDau = 0;"
        "      for (const bia of doc.querySelectorAll('.bia')) {"
        "        if (!dangHienThi(bia, win)) continue;"
        "        const br = bia.getBoundingClientRect();"
        "        if (br.top >= -SAI_SO && br.bottom <= gioiHanCao + SAI_SO) {"
        "          soBiaManDau += 1;"
        "        }"
        "      }"
        "      if (BE_RONG === 1440 && soBiaManDau < NGUONG_BIA_1440) {"
        "        loi.push({loai: 'trang_chu_1440', moTa: '.bia', chiTiet: 'chi co ' + soBiaManDau + ' bia trong ' + CAO_MAN_DAU_1440 + 'px dau (can >= ' + NGUONG_BIA_1440 + ')'});"
        "      }"
        "      if (BE_RONG === 390) {"
        "        if (soBiaManDau < NGUONG_BIA_390) {"
        "          loi.push({loai: 'trang_chu_390', moTa: '.bia', chiTiet: 'chi co ' + soBiaManDau + ' bia trong ' + CAO_MAN_DAU + 'px dau (can >= ' + NGUONG_BIA_390 + ')'});"
        "        }"
        "        let soNutMuaManDau = 0;"
        "        for (const nut of doc.querySelectorAll('form[action=\"/gio/them\"] button[type=\"submit\"]')) {"
        "          if (!dangHienThi(nut, win)) continue;"
        "          const nr = nut.getBoundingClientRect();"
        "          if (nr.top >= -SAI_SO && nr.bottom <= CAO_MAN_DAU + SAI_SO) {"
        "            soNutMuaManDau += 1;"
        "          }"
        "        }"
        "        if (soNutMuaManDau < NGUONG_NUT_MUA_390) {"
        "          loi.push({loai: 'trang_chu_390', moTa: 'form[action=\"/gio/them\"] button[type=\"submit\"]', chiTiet: 'chi co ' + soNutMuaManDau + ' nut mua trong ' + CAO_MAN_DAU + 'px dau (can >= ' + NGUONG_NUT_MUA_390 + ')'});"
        "        }"
        "      }"
        "    }"
        "    if (BE_RONG === 390 && m.trang === 'chi_tiet.html') {"
        "      const giaEl = doc.querySelector('.chi-tiet__gia');"
        "      const nutMua = doc.querySelector('.form-them-chi-tiet button[type=\"submit\"]');"
        "      if (!giaEl || !dangHienThi(giaEl, win)) {"
        "        loi.push({loai: 'chi_tiet_390', moTa: '.chi-tiet__gia', chiTiet: 'khong hien thi tren 390px'});"
        "      } else {"
        "        const gr = giaEl.getBoundingClientRect();"
        "        if (gr.bottom > CAO_MAN_DAU + SAI_SO) {"
        "          loi.push({loai: 'chi_tiet_390', moTa: '.chi-tiet__gia', chiTiet: 'bottom=' + Math.round(gr.bottom) + 'px > ' + CAO_MAN_DAU + 'px'});"
        "        }"
        "      }"
        "      if (!nutMua || !dangHienThi(nutMua, win)) {"
        "        loi.push({loai: 'chi_tiet_390', moTa: '.form-them-chi-tiet button[type=\"submit\"]', chiTiet: 'khong hien thi tren 390px'});"
        "      } else {"
        "        const nr = nutMua.getBoundingClientRect();"
        "        if (nr.bottom > CAO_MAN_DAU + SAI_SO) {"
        "          loi.push({loai: 'chi_tiet_390', moTa: moTa(nutMua), chiTiet: 'bottom=' + Math.round(nr.bottom) + 'px > ' + CAO_MAN_DAU + 'px'});"
        "        }"
        "      }"
        "    }"
        "    if (BE_RONG === 390) {"
        "      const menuQl = doc.querySelector('.menu-ql');"
        "      if (menuQl) {"
        "        if (menuQl.scrollWidth > menuQl.clientWidth + SAI_SO) {"
        "          loi.push({loai: 'menu_ql_390', moTa: '.menu-ql', chiTiet: 'bi cuon ngang an (scrollWidth=' + Math.round(menuQl.scrollWidth) + ' > clientWidth=' + Math.round(menuQl.clientWidth) + ')'});"
        "        }"
        "        for (const muc of menuQl.querySelectorAll('.menu-ql__muc')) {"
        "          if (!dangHienThi(muc, win)) {"
        "            loi.push({loai: 'menu_ql_390', moTa: moTa(muc), chiTiet: 'bi an tren 390px'});"
        "            continue;"
        "          }"
        "          const mr = muc.getBoundingClientRect();"
        "          if (mr.left < -SAI_SO || mr.right > BE_RONG + SAI_SO) {"
        "            loi.push({loai: 'menu_ql_390', moTa: moTa(muc), chiTiet: 'vuot man 390px (left=' + Math.round(mr.left) + ', right=' + Math.round(mr.right) + ')'});"
        "          }"
        "        }"
        "      }"
        "      if (m.trang === 'danh_sach.html') {"
        "        const locNd = doc.querySelector('.bo-loc-noi-dung');"
        "        if (locNd && dangHienThi(locNd, win)) {"
        "          loi.push({loai: 'bo_loc_390', moTa: '.bo-loc-noi-dung', chiTiet: 'bo loc khong thu gon mac dinh o 390px'});"
        "        }"
        "        const theDau = doc.querySelector('.cot-ket-qua .the-sach');"
        "        if (theDau) {"
        "          const tr = theDau.getBoundingClientRect();"
        "          if (tr.top >= CAO_MAN_DAU) {"
        "            loi.push({loai: 'bo_loc_390', moTa: '.cot-ket-qua .the-sach', chiTiet: 'the sach dau tien bi day xuong top=' + Math.round(tr.top) + 'px >= ' + CAO_MAN_DAU + 'px'});"
        "          }"
        "        }"
        "      }"
        "    }"
        "    let soAnhBia = 0;"
        "    for (const img of doc.querySelectorAll('.bia img.bia__anh')) {"
        "      if (!dangHienThi(img, win)) continue;"
        "      soAnhBia += 1;"
        "      const ir = img.getBoundingClientRect();"
        "      const tiLe = ir.width / ir.height;"
        "      if (Math.abs(tiLe - TI_LE_BIA) > SAI_SO_TI_LE) {"
        "        loi.push({loai: 'ti_le_bia', moTa: moTa(img), chiTiet: 'ti le hien thi ' + tiLe.toFixed(3) + ' (' + Math.round(ir.width) + 'x' + Math.round(ir.height) + 'px), khac 2:3 (~0.667)'});"
        "      }"
        "      const ics = win.getComputedStyle(img);"
        "      if (ics.objectFit !== 'cover') {"
        "        loi.push({loai: 'ti_le_bia', moTa: moTa(img), chiTiet: 'object-fit=' + ics.objectFit + ' (can cover de khong meo bia)'});"
        "      }"
        "      if ((img.loading !== 'lazy' || ir.top < 900) && (!img.complete || img.naturalWidth === 0)) {"
        "        loi.push({loai: 'anh_bia_loi', moTa: moTa(img), chiTiet: 'anh bia khong tai duoc (src=' + (img.getAttribute('src') || '') + ')'});"
        "      }"
        "    }"
        "    return {trang: m.trang, beRong: BE_RONG, soAnhBia, loi};"
        "  });"
        "  document.getElementById('ket-qua-bo-cuc').textContent = 'KET_QUA_BC:' + JSON.stringify(kq);"
        "});"
        "</script></body></html>"
    )


class MayChuDaLuong(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


def chay_do(cac_trang: list[str], thu_muc_goc: Path = GOC) -> list[dict]:
    edge = tim_edge()
    lo_map: dict[str, str] = {}
    for be_rong in CAC_BE_RONG:
        for i in range(0, len(cac_trang), SO_TRANG_MOI_LO):
            nhom = cac_trang[i : i + SO_TRANG_MOI_LO]
            lo_map[f"/__bc_{be_rong}_{i}"] = tao_html_do(nhom, be_rong)

    class TrinhPhucVu(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(thu_muc_goc), **kwargs)

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
    with tempfile.TemporaryDirectory(prefix="edge_bo_cuc_") as thu_muc_ho_so:
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
                        f"--user-data-dir={ho_so_lo}",
                        "--dump-dom",
                        f"http://127.0.0.1:{cong}{duong}",
                    ]
                    cp = subprocess.run(
                        lenh,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=60,
                    )
                    m = re.search(r"KET_QUA_BC:(\[.*?\])</pre>", cp.stdout, flags=re.S)
                    if not m:
                        raise RuntimeError(
                            f"Khong doc duoc ket qua do {duong} (rc={cp.returncode}): {cp.stderr[:300]}"
                        )
                    ket_qua.extend(json.loads(html.unescape(m.group(1))))
            finally:
                may_chu.shutdown()
    return ket_qua


def main() -> int:
    cac_trang = sorted(p.name for p in THU_MUC_XEM_TRUOC.glob("*.html"))
    if not cac_trang:
        print("Khong tim thay trang HTML nao trong xem_truoc/", file=sys.stderr)
        return 1

    ket_qua = chay_do(cac_trang)
    tong_loi = 0
    tong_anh_bia = 0
    for muc in ket_qua:
        tong_anh_bia += muc.get("soAnhBia", 0)
        for loi in muc["loi"]:
            tong_loi += 1
            print(
                f"LOI [{loi['loai']}] {muc['trang']} @ {muc['beRong']}px | "
                f"{loi['moTa']} -> {loi['chiTiet']}"
            )

    if tong_anh_bia == 0:
        tong_loi += 1
        print("LOI [ti_le_bia] Khong tim thay anh bia that (.bia img.bia__anh) nao trong xem_truoc/.")

    if tong_loi > 0:
        print(
            f"KHONG DAT: {tong_loi} loi bo cuc tren {len(cac_trang)} trang "
            f"(cac be rong {list(CAC_BE_RONG)}px)."
        )
        return 1

    print(
        f"DAT: {len(cac_trang)} trang o {list(CAC_BE_RONG)}px — "
        f"o tim kiem <= {int(GIOI_HAN_TIM_KIEM_PX)}px dau trang, 0 loi cat/an chu, "
        f"moi trang dung 1 h1 khong nhay bac, chi_tiet/menu_ql/bo_loc 390px deu dat, "
        f"{tong_anh_bia} luot anh bia dung ti le 2:3."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
