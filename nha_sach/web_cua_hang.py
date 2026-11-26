"""Blueprint các trang và thao tác của khách."""
import re
from dataclasses import asdict
from secrets import token_urlsafe
from types import SimpleNamespace

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from markupsafe import Markup
from werkzeug.local import LocalProxy

from .loi import KhongTimThay, LoiNghiepVu
from .mo_hinh import SoDienThoai
from .phien import GioiHanThu
from .qr import thong_tin_qr


bp = Blueprint("cua_hang", __name__)
_cau_hinh = LocalProxy(lambda: current_app.extensions["web_cua_hang"])
cua_hang = LocalProxy(lambda: _cau_hinh.dich_vu)
quan_ly = LocalProxy(lambda: _cau_hinh.quan_ly)
thu_khach = LocalProxy(lambda: _cau_hinh.thu_khach)
thu_tra_cuu = LocalProxy(lambda: _cau_hinh.thu_tra_cuu)


def tao_cua_hang(dich_vu, quan_ly):
    current_app.extensions["web_cua_hang"] = SimpleNamespace(
        dich_vu=dich_vu, quan_ly=quan_ly, thu_khach=GioiHanThu(), thu_tra_cuu=GioiHanThu(),
    )
    return bp


def ma_vua_xem():
    return session.get("vua_xem", [])


@bp.get("/")
def trang_chu():
    return render_template("trang_chu.html", **cua_hang.trang_chu(ma_vua_xem()))

@bp.get("/sach")
def danh_sach():
    bo_loc = dict(
        q=request.args.get("q", "").strip(),
        danh_muc=request.args.get("danh_muc", "").strip(),
        gia_tu=request.args.get("gia_tu", type=int),
        gia_den=request.args.get("gia_den", type=int),
        sap_xep=request.args.get("sap_xep") or None,
        tac_gia=request.args.get("tac_gia", "").strip(),
        giam_gia=request.args.get("giam_gia") == "1",
        con_hang=request.args.get("con_hang") == "1",
        co_review=request.args.get("co_review") == "1",
        trang=request.args.get("trang", 1, type=int),
    )
    return render_template("danh_sach.html", **cua_hang.tim_sach(**bo_loc))

@bp.get("/api/goi-y")
def goi_y():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    return jsonify([
        dict(ma=sach.ma, tieu_de=sach.tieu_de, tac_gia=sach.tac_gia, gia=sach.gia,
             anh_bia=sach.anh_bia, bia=None if sach.anh_bia else asdict(sach.bia),
             mau_bia=sach.mau_bia, con_hang=sach.ton_kho > 0)
        for sach in cua_hang.goi_y_sach(q)
    ])


@bp.get("/sach/<int:ma>")
def chi_tiet(ma):
    try:
        du_lieu = cua_hang.chi_tiet_sach(ma, ma_vua_xem())
    except KhongTimThay:
        abort(404)
    if request.method == "GET":
        session["vua_xem"] = [ma, *(muc for muc in ma_vua_xem() if muc != ma)][:8]
    co_the, cua_toi = cua_hang.thong_tin_danh_gia(ma, g.khach.ma if g.khach else None)
    return render_template(
        "chi_tiet.html", **du_lieu, co_the_danh_gia=co_the, danh_gia_cua_toi=cua_toi,
    )

def gio_hang():
    return {int(ma): so_luong for ma, so_luong in session.get("gio", {}).items()}

def luu_gio(gio):
    session["gio"] = {str(ma): so_luong for ma, so_luong in gio.items()}

def duong_noi_bo(tiep, mac_dinh):
    if tiep.startswith("/") and not tiep.startswith("//") and "\\" not in tiep:
        if not any(ord(c) < 32 for c in tiep):
            return tiep
    return mac_dinh

def tinh_gio_phien(gio):
    ma = session.get("ma_giam_gia")
    xem = cua_hang.xem_gio(gio, ma)
    if ma and (xem.ma_giam_gia is None or not xem.muc):
        session.pop("ma_giam_gia", None)
        flash(xem.loi_ma_giam_gia or f"Đã bỏ mã {ma} vì giỏ hàng đang trống.", "loi")
        return cua_hang.xem_gio(gio)
    return xem

@bp.get("/gio")
def xem_gio():
    gio = gio_hang()
    xem = tinh_gio_phien(gio)
    con_ban = {muc.sach.ma for muc in xem.muc}
    if gio.keys() - con_ban:
        luu_gio({ma: so_luong for ma, so_luong in gio.items() if ma in con_ban})
    return render_template("gio_hang.html", gio=xem)

@bp.post("/gio/them")
@bp.post("/gio/sua")
def cap_nhat_gio():
    them = request.path == "/gio/them"
    tra_json = them and request.accept_mimetypes["application/json"] > 0 and any(
        kieu == "application/json" for kieu, _ in request.accept_mimetypes
    )
    ma = request.form.get("ma", type=int)
    so_luong = request.form.get("so_luong", type=int)
    if them and "so_luong" not in request.form:
        so_luong = 1
    gio = gio_hang()
    try:
        if not ma or so_luong is None or so_luong < (1 if them else 0):
            raise LoiNghiepVu("Số lượng không hợp lệ.")
        neu_luu = gio.get(ma, 0) + so_luong if them else so_luong
        if neu_luu:
            sach = cua_hang.sach_dang_ban(ma)
            if neu_luu > sach.ton_kho:
                raise LoiNghiepVu("Số lượng vượt tồn kho.")
            gio[ma] = neu_luu
        else:
            gio.pop(ma, None)
        luu_gio(gio)
        if session.get("ma_giam_gia"):
            tinh_gio_phien(gio)
        if tra_json:
            return jsonify(ok=True, so_trong_gio=sum(gio.values()), ten_sach=sach.tieu_de)
        if them:
            flash(Markup('Đã thêm «{}» vào giỏ. <a href="{}">Xem giỏ hàng</a>.').format(
                sach.tieu_de, url_for("xem_gio"),
            ), "tot")
    except LoiNghiepVu as exc:
        if tra_json:
            return jsonify(ok=False, so_trong_gio=sum(gio.values()), ten_sach=None, loi=str(exc)), 400
        flash(str(exc), "loi")
    return redirect(duong_noi_bo(request.form.get("tiep", ""), url_for("xem_gio")))

@bp.post("/gio/ma-giam-gia")
@bp.post("/gio/bo-ma")
def doi_ma_giam_gia():
    if request.path == "/gio/bo-ma":
        session.pop("ma_giam_gia", None)
    else:
        ma = request.form.get("ma_giam_gia", "").strip().upper()
        gio = cua_hang.xem_gio(gio_hang(), ma)
        if gio.ma_giam_gia is None or not gio.muc:
            flash(gio.loi_ma_giam_gia or "Hãy thêm sách vào giỏ trước khi áp mã.", "loi")
        else:
            session["ma_giam_gia"] = gio.ma_giam_gia.ma
            flash("Đã áp dụng mã giảm giá.", "tot")
    return redirect(duong_noi_bo(request.form.get("tiep", ""), url_for("xem_gio")))

def _doi_ma_o_dat_hang(gio, hanh_dong, ma):
    if hanh_dong == "bo_ma":
        session.pop("ma_giam_gia", None)
        return cua_hang.xem_gio(gio), "", {}
    xem = cua_hang.xem_gio(gio, ma)
    if xem.ma_giam_gia is None or not xem.muc:
        loi = xem.loi_ma_giam_gia or "Hãy nhập mã giảm giá và thêm sách vào giỏ."
        return cua_hang.xem_gio(gio, session.get("ma_giam_gia")), ma, {"ma_giam_gia": loi}
    session["ma_giam_gia"] = xem.ma_giam_gia.ma
    return xem, ma, {}


@bp.route("/dat-hang", methods=["GET", "POST"])
def dat_hang():
    gio = gio_hang()
    ma_giam_gia = session.get("ma_giam_gia")
    if request.method == "POST" and "ma_giam_gia" in request.form:
        ma_giam_gia = request.form["ma_giam_gia"].strip().upper() or None
    xem = tinh_gio_phien(gio) if request.method == "GET" else None
    if request.method == "GET":
        ma_giam_gia = session.get("ma_giam_gia")
    ma_thao_tac = session.get("ma_thao_tac_dat_hang")
    if ma_thao_tac is None:
        ma_thao_tac = session["ma_thao_tac_dat_hang"] = token_urlsafe(24)
    mac_dinh = {ten: "" for ten in ("ho_ten", "dien_thoai", "dia_chi", "ghi_chu")}
    mac_dinh["phuong_thuc"] = "cod"
    if g.khach:
        mac_dinh.update(ho_ten=g.khach.ho_ten, dien_thoai=g.khach.dien_thoai, dia_chi=g.khach.dia_chi)
    loi, loi_truong = None, {}
    if request.method == "POST":
        mac_dinh.update({ten: request.form.get(ten, "") for ten in mac_dinh})
        hanh_dong = request.form.get("hanh_dong", "dat")
        if hanh_dong in ("ap_ma", "bo_ma"):
            xem, ma_giam_gia, loi_truong = _doi_ma_o_dat_hang(gio, hanh_dong, ma_giam_gia or "")
            return render_template(
                "dat_hang.html", gio=xem, ma_giam_gia=ma_giam_gia,
                mac_dinh=mac_dinh, ma_thao_tac=ma_thao_tac, loi=None, loi_truong=loi_truong,
            ), 400 if loi_truong else 200
        if hanh_dong != "dat":
            abort(400)
        ma_gui = request.form.get("ma_thao_tac", "")
        ma_truoc = session.get("ma_thao_tac_dat_hang_truoc")
        try:
            if ma_gui not in (ma_thao_tac, ma_truoc):
                raise LoiNghiepVu("Hãy tải lại trang đặt hàng.")
            don = cua_hang.dat_hang(
                gio, mac_dinh, ma_gui, ma_giam_gia, g.khach.ma if g.khach else None,
            )
            if ma_gui == ma_thao_tac:
                session["ma_thao_tac_dat_hang_truoc"] = ma_gui
                session.pop("ma_thao_tac_dat_hang", None)
                luu_gio({})
                session.pop("ma_giam_gia", None)
            session["don_da_xac_minh"] = danh_sach_ma_don(don.ma_tra_cuu)
            flash("Đặt hàng thành công. Hãy lưu mã tra cứu để theo dõi đơn.", "tot")
            return redirect(url_for("xem_don", ma_tra_cuu=don.ma_tra_cuu))
        except LoiNghiepVu as exc:
            loi = str(exc)
            loi_truong = getattr(exc, "loi_truong", {})
            xem = cua_hang.xem_gio(gio, ma_giam_gia)
    return render_template(
        "dat_hang.html", gio=xem, ma_giam_gia=ma_giam_gia or "",
        mac_dinh=mac_dinh, ma_thao_tac=ma_thao_tac, loi=loi, loi_truong=loi_truong,
    ), 400 if loi else 200

def danh_sach_ma_don(ma):
    return [item for item in session.get("don_da_xac_minh", []) if item != ma][-19:] + [ma]

@bp.route("/tra-cuu", methods=["GET", "POST"])
def tra_cuu():
    loi, loi_truong = None, {}
    form = {"ma": request.values.get("ma", ""), "dien_thoai": request.form.get("dien_thoai", "")}
    if request.method == "POST":
        if SoDienThoai.chuan_hoa(form["dien_thoai"]) is None:
            loi_truong["dien_thoai"] = "Nhập số điện thoại Việt Nam gồm 10 chữ số."
        ma = form["ma"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{8}", ma):
            loi_truong["ma"] = "Mã tra cứu gồm 8 chữ cái hoặc chữ số."
        if not loi_truong and not thu_tra_cuu.ghi_nhan(ma):
            abort(429, "Hãy đợi 15 phút rồi thử tra cứu lại.")
        don = None if loi_truong else cua_hang.tra_cuu(ma, form["dien_thoai"])
        if don:
            thu_tra_cuu.xoa(ma)
            session["don_da_xac_minh"] = danh_sach_ma_don(don.ma_tra_cuu)
            return redirect(url_for("xem_don", ma_tra_cuu=don.ma_tra_cuu))
        loi = "Mã tra cứu hoặc số điện thoại không khớp."
    return render_template("tra_cuu.html", loi=loi, form=form, loi_truong=loi_truong)

def don_co_quyen_xem(ma_tra_cuu):
    try:
        don = cua_hang.lay_don(ma_tra_cuu)
    except KhongTimThay:
        return None
    if don.ma_tra_cuu in session.get("don_da_xac_minh", []) or (g.khach and don.ma_khach == g.khach.ma):
        return don
    return None

@bp.get("/don/<ma_tra_cuu>")
def xem_don(ma_tra_cuu):
    don = don_co_quyen_xem(ma_tra_cuu)
    if don is None:
        return redirect(url_for("tra_cuu", ma=ma_tra_cuu))
    qr_svg, ngan_hang = thong_tin_qr(don, current_app.config["NGAN_HANG"])
    return render_template(
        "don_hang.html", don=don, qr_svg=qr_svg, ngan_hang=ngan_hang,
        co_the_huy=don.khach_co_the_huy(),
    )

@bp.post("/don/<ma_tra_cuu>/huy")
def huy_don(ma_tra_cuu):
    don = don_co_quyen_xem(ma_tra_cuu)
    if don is None:
        return redirect(url_for("tra_cuu", ma=ma_tra_cuu))
    if request.form.get("xac_nhan") != "1":
        abort(400, "Hãy xác nhận bạn muốn hủy đơn hàng.")
    try:
        quan_ly.doi_trang_thai(don.ma, "da_huy", khach_huy=True)
        flash("Đã hủy đơn hàng.", "tot")
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
    return redirect(url_for("xem_don", ma_tra_cuu=ma_tra_cuu))

@bp.route("/dang-ky", methods=["GET", "POST"])
def dang_ky():
    form, loi_truong = {}, {}
    if request.method == "POST":
        form = {ten: request.form.get(ten, "") for ten in ("ho_ten", "email", "dien_thoai")}
        try:
            khach = cua_hang.dang_ky(
                **form, mat_khau=request.form.get("mat_khau", ""),
                mat_khau_lai=request.form.get("mat_khau_lai", ""),
            )
        except LoiNghiepVu as exc:
            loi_truong = getattr(exc, "loi_truong", {})
            flash(str(exc), "loi")
        else:
            session["ma_khach"] = khach.ma
            session.pop("csrf", None)
            return redirect(url_for("tai_khoan"))
    return render_template("tai_khoan/dang_ky.html", form=form, loi_truong=loi_truong)

@bp.route("/dang-nhap", methods=["GET", "POST"])
def dang_nhap():
    form = {"email": "", "tiep": request.args.get("tiep", "")}
    if request.method == "POST":
        form.update({ten: request.form.get(ten, "") for ten in form})
        ip = request.remote_addr
        if not thu_khach.ghi_nhan(ip):
            abort(429, "Bạn đã thử đăng nhập quá nhiều lần. Hãy thử lại sau 15 phút.")
        khach = cua_hang.dang_nhap(form["email"], request.form.get("mat_khau", ""))
        if khach:
            thu_khach.xoa(ip)
            session["ma_khach"] = khach.ma
            session.pop("csrf", None)
            return redirect(duong_noi_bo(form["tiep"], url_for("tai_khoan")))
        flash("Email hoặc mật khẩu không đúng.", "loi")
    return render_template("tai_khoan/dang_nhap.html", form=form)

@bp.post("/dang-xuat")
def dang_xuat():
    session.pop("ma_khach", None)
    session.pop("don_da_xac_minh", None)
    session.pop("csrf", None)
    return redirect(url_for("trang_chu"))

@bp.get("/tai-khoan")
def tai_khoan():
    if g.khach is None:
        return redirect(url_for("dang_nhap", tiep=request.path))
    ho_so = {ten: getattr(g.khach, ten) for ten in ("ho_ten", "dien_thoai", "dia_chi")}
    return _trang_tai_khoan(ho_so, {})


@bp.post("/tai-khoan/ho-so")
def sua_ho_so():
    if g.khach is None:
        return redirect(url_for("dang_nhap", tiep=url_for("tai_khoan")))
    ho_so = {ten: request.form.get(ten, "") for ten in ("ho_ten", "dien_thoai", "dia_chi")}
    try:
        cua_hang.cap_nhat_ho_so(g.khach.ma, **ho_so)
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
        return _trang_tai_khoan(ho_so, getattr(exc, "loi_truong", {})), 400
    flash("Đã cập nhật hồ sơ.", "tot")
    return redirect(url_for("tai_khoan"))


def _trang_tai_khoan(ho_so, loi_truong):
    return render_template(
        "tai_khoan/don_cua_toi.html", don=cua_hang.don_cua_khach(g.khach.ma),
        ho_so=ho_so, loi_truong=loi_truong,
    )

@bp.post("/sach/<int:ma>/danh-gia")
def danh_gia_sach(ma):
    chi_tiet_url = url_for("chi_tiet", ma=ma)
    if g.khach is None:
        return redirect(url_for("dang_nhap", tiep=chi_tiet_url))
    try:
        cua_hang.luu_danh_gia(
            ma, g.khach.ma, request.form.get("so_sao", type=int),
            request.form.get("noi_dung", ""),
        )
        flash("Đã lưu đánh giá.", "tot")
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
    return redirect(chi_tiet_url)
