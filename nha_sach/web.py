"""Khởi tạo Flask, gắn dịch vụ và đăng ký các Blueprint."""
import hmac
from pathlib import Path
from secrets import token_urlsafe

from flask import Flask, abort, current_app, g, render_template, request, send_from_directory, session

from .dich_vu import tao_dich_vu
from .du_lieu import nap_mau
from .phien import PhienQuanLy
from .web_cua_hang import tao_cua_hang
from .web_quan_ly import tao_quan_ly


GOC = Path(__file__).resolve().parents[1]


def create_app(cau_hinh=None, *, dich_vu=None):
    app = _tao_flask(cau_hinh)
    phien_quan_ly = PhienQuanLy()
    if dich_vu is None:
        cua_hang, quan_ly = tao_dich_vu(app.config["NHA_SACH_DB"])
        if app.config["NAP_DU_LIEU_MAU"]:
            nap_mau(cua_hang.csdl, GOC / "du_lieu" / "sach_mau.json")
    else:
        cua_hang, quan_ly = dich_vu

    app.extensions["nha_sach_cua_hang"] = cua_hang
    app.extensions["nha_sach_quan_ly"] = quan_ly
    _gan_dung_chung(app, cua_hang, phien_quan_ly)
    with app.app_context():
        app.register_blueprint(tao_cua_hang(cua_hang, quan_ly))
        app.register_blueprint(tao_quan_ly(
            quan_ly, app.config["NHA_SACH_MAT_KHAU"], app.config["CUA_HANG"],
            app.config["THU_MUC_ANH"], phien_quan_ly,
        ))
    app.add_url_rule("/bia-ebook/<ten>", view_func=bia_ebook)
    app.url_build_error_handlers.append(_url_cua_hang_ten_cu(app))
    return app


def bia_ebook(ten):
    if Path(ten).suffix.lower() not in {".jpg", ".png", ".webp"}:
        abort(404)
    return send_from_directory(GOC / "du_lieu" / "bia", ten)


def _url_cua_hang_ten_cu(app):
    # Tên endpoint cũ vẫn dùng được khi tạo URL mà không cần đăng ký route trùng.
    def chuyen_ten(loi, endpoint, gia_tri):
        ten_moi = f"cua_hang.{endpoint}"
        if ten_moi in app.view_functions:
            return app.url_for(ten_moi, **gia_tri)
        return None
    return chuyen_ten


def _tao_flask(cau_hinh):
    cau_hinh = dict(cau_hinh or {})
    template_folder = cau_hinh.pop("template_folder", str(GOC / "templates"))
    app = Flask(__name__, template_folder=template_folder, static_folder=str(GOC / "static"))
    app.config.from_mapping(
        SECRET_KEY=token_urlsafe(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        NHA_SACH_DB=GOC / "nha_sach.db",
        NHA_SACH_MAT_KHAU="admin",
        NAP_DU_LIEU_MAU=False,
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        THU_MUC_ANH=GOC / 'static' / 'uploads',
        NGAN_HANG={},
        CUA_HANG={"ten": "Nhà Sách Tri Thức", "dia_chi": "128 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh",
                  "dien_thoai": "19006868"},
    )
    cua_hang_config = app.config["CUA_HANG"] | cau_hinh.get("CUA_HANG", {})
    app.config.update(cau_hinh)
    app.config["CUA_HANG"] = cua_hang_config
    return app


def _gan_dung_chung(app, cua_hang, phien_quan_ly):
    @app.before_request
    def chuan_bi():
        g.khach = cua_hang.lay_khach(session.get("ma_khach"))
        if "csrf" not in session:
            session["csrf"] = token_urlsafe(32)
        if request.method == "POST":
            gui = request.form.get("csrf", "").encode()
            if not hmac.compare_digest(session["csrf"].encode(), gui):
                abort(400, "Hãy tải lại trang và thử lại.")

    @app.context_processor
    def bien_chung():
        return dict(
            csrf=session["csrf"], khach=g.khach,
            la_quan_ly=phien_quan_ly.hop_le(session.get("quan_ly")),
            so_trong_gio=sum(session.get("gio", {}).values()),
            danh_muc_menu=cua_hang.danh_muc(),
        )

    @app.after_request
    def header(phan_hoi):
        phan_hoi.headers["X-Content-Type-Options"] = "nosniff"
        phan_hoi.headers["X-Frame-Options"] = "DENY"
        phan_hoi.headers["Referrer-Policy"] = "same-origin"
        return phan_hoi

    @app.template_filter("tien")
    def tien(so):
        return f"{so:,}".replace(",", ".") + " đ"

    @app.template_filter("ngay")
    def ngay(luc):
        return luc.strftime("%d/%m/%Y %H:%M")

    app.register_error_handler(400, trang_loi)
    for ma in (404, 413, 429, 500):
        app.register_error_handler(ma, trang_loi)


def trang_loi(exc):
    tieu_de = {
        404: "Không tìm thấy trang", 413: "Dữ liệu tải lên quá lớn",
        429: "Quá nhiều lần thử", 500: "Có lỗi khi xử lý yêu cầu",
    }.get(exc.code, "Yêu cầu không hợp lệ")
    if not current_app.jinja_env.list_templates(filter_func=lambda ten: ten == "loi.html"):
        return exc
    return render_template(
        "loi.html", ma_loi=exc.code, tieu_de=tieu_de, thong_bao=exc.description,
    ), exc.code
