"""Các route quản lý và kiểm tra quyền truy cập."""
from secrets import token_urlsafe
from types import SimpleNamespace

from werkzeug.security import check_password_hash, generate_password_hash

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, session, url_for

from .anh_bia import luu_anh_bia
from .loi import KhongTimThay, LoiNghiepVu
from .xuat import dong_don, tao_csv
from .phien import GioiHanThu


from werkzeug.local import LocalProxy


bp = Blueprint("quan_ly", __name__, url_prefix="/quan-ly")
_cau_hinh = LocalProxy(lambda: current_app.extensions["web_quan_ly"])
dich_vu = LocalProxy(lambda: _cau_hinh.dich_vu)
phien = LocalProxy(lambda: _cau_hinh.phien)
thu = LocalProxy(lambda: _cau_hinh.thu)


def tao_quan_ly(dich_vu, mat_khau, cua_hang, thu_muc_anh, phien):
    current_app.extensions["web_quan_ly"] = SimpleNamespace(
        dich_vu=dich_vu, cua_hang=cua_hang, thu_muc_anh=thu_muc_anh, phien=phien,
        thu=GioiHanThu(), mac_dinh=mat_khau == "admin", mat_khau_bam=generate_password_hash(mat_khau),
    )
    return bp


@bp.before_request
def kiem_quyen():
    if request.endpoint != "quan_ly.dang_nhap" and not phien.hop_le(session.get("quan_ly")):
        return redirect(url_for("quan_ly.dang_nhap"))

@bp.route("/dang-nhap", methods=["GET", "POST"])
def dang_nhap():
    if request.method == "POST":
        ip = request.remote_addr
        if not thu.ghi_nhan(ip):
            abort(429, "Bạn đã thử đăng nhập quá nhiều lần. Hãy thử lại sau 15 phút.")
        nhap = request.form.get("mat_khau", "")
        if len(nhap) <= 256 and check_password_hash(_cau_hinh.mat_khau_bam, nhap):
            thu.xoa(ip)
            phien.xoa(session.get("quan_ly"))
            session["quan_ly"] = phien.tao()
            session.pop("csrf", None)
            return redirect(url_for("quan_ly.tong_quan"))
        flash("Mật khẩu quản lý không đúng.", "loi")
    return render_template("quan_ly/dang_nhap.html")

@bp.post("/dang-xuat")
def dang_xuat():
    phien.xoa(session.pop("quan_ly", None))
    session.pop("csrf", None)
    return redirect(url_for("quan_ly.dang_nhap"))

@bp.get("/")
def tong_quan():
    if _cau_hinh.mac_dinh:
        flash("Đang dùng mật khẩu mặc định.", "loi")
    return render_template("quan_ly/tong_quan.html", **dich_vu.tong_quan())

@bp.get("/don")
def danh_sach_don():
    try:
        du_lieu = dich_vu.danh_sach_don(
            request.args.get("trang_thai"), request.args.get("trang", 1, type=int),
            q=request.args.get("q", "").strip(),
        )
    except LoiNghiepVu as exc:
        abort(400, str(exc))
    return render_template("quan_ly/don.html", **du_lieu)

def lay_don(ma):
    try:
        return dich_vu.lay_don(ma)
    except KhongTimThay as exc:
        abort(404, str(exc))

@bp.get("/don/<int:ma>")
def chi_tiet_don(ma):
    don = lay_don(ma)
    return render_template("quan_ly/chi_tiet_don.html", don=don, buoc_tiep=don.buoc_hop_le())

@bp.post("/don/<int:ma>/trang-thai")
@bp.post("/don/<int:ma>/huy")
def doi_trang_thai(ma):
    trang_thai = "da_huy" if request.path.endswith("/huy") else request.form.get("trang_thai")
    if trang_thai == "da_huy" and request.form.get("xac_nhan") != "1":
        abort(400, "Hãy xác nhận bạn muốn hủy đơn hàng.")
    try:
        dich_vu.doi_trang_thai(
            ma, trang_thai,
            da_hoan_tien=request.form.get("da_hoan_tien") in ("1", "on", "true"),
        )
        flash("Đã cập nhật trạng thái đơn hàng.", "tot")
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
    return redirect(url_for("quan_ly.chi_tiet_don", ma=ma))

@bp.post("/don/<int:ma>/da-thanh-toan")
def da_thanh_toan(ma):
    try:
        dich_vu.xac_nhan_thanh_toan(ma)
        flash("Đã xác nhận thanh toán.", "tot")
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
    return redirect(url_for("quan_ly.chi_tiet_don", ma=ma))

@bp.get("/don/<int:ma>/hoa-don")
def hoa_don(ma):
    return render_template("quan_ly/hoa_don.html", don=lay_don(ma), cua_hang=_cau_hinh.cua_hang)

@bp.get("/khach-hang")
def khach_hang():
    return render_template("quan_ly/khach_hang.html", khach_hang=dich_vu.danh_sach_khach())

def phan_hoi_csv(ten, cot, dong):
    return Response(
        tao_csv(cot, dong), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={ten}"},
    )

@bp.get("/xuat/don.csv")
def xuat_don():
    return phan_hoi_csv(
        "don.csv",
        ("Mã tra cứu", "Họ tên", "Điện thoại", "Địa chỉ", "Trạng thái", "Phương thức",
         "Tạm tính", "Giảm giá", "Phí giao", "Tổng", "Tạo lúc"),
        (dong_don(row) for row in dich_vu.xuat_don()),
    )

@bp.get("/xuat/doanh-thu.csv")
def xuat_doanh_thu():
    theo_ngay = dich_vu.doanh_thu()
    theo_thang = dich_vu.gop_doanh_thu_thang(theo_ngay)
    dong = [*theo_ngay.items(), (), ("Tháng", "Doanh thu"), *theo_thang.items()]
    return phan_hoi_csv("doanh-thu.csv", ("Ngày", "Doanh thu"), dong)

@bp.get("/sach")
def danh_sach_sach():
    return render_template("quan_ly/sach.html", **dich_vu.danh_sach_sach(
        q=request.args.get("q", ""), danh_muc=request.args.get("danh_muc", ""),
        trang=request.args.get("trang", 1, type=int), loc=request.args.get("loc", ""),
    ))

@bp.route("/sach/moi", methods=["GET", "POST"])
@bp.route("/sach/<int:ma>/sua", methods=["GET", "POST"])
def sua_sach(ma=None):
    try:
        sach = dich_vu.lay_sach(ma) if ma is not None else None
    except KhongTimThay as exc:
        abort(404, str(exc))
    ma_thao_tac = request.form.get("ma_thao_tac") or token_urlsafe(24)
    loi_truong = {}
    if request.method == "POST":
        tep_moi = None
        try:
            tep_moi = luu_anh_bia(request.files.get("anh_bia"), _cau_hinh.thu_muc_anh)
            url = f"/static/uploads/{tep_moi.name}" if tep_moi else None
            _, da_luu = dich_vu.luu_sach(request.form, ma, url)
        except LoiNghiepVu as exc:
            loi_truong = getattr(exc, "loi_truong", {})
            if tep_moi:
                tep_moi.unlink(missing_ok=True)
            flash(str(exc), "loi")
        except Exception:
            if tep_moi:
                tep_moi.unlink(missing_ok=True)
            raise
        else:
            if tep_moi and not da_luu:
                tep_moi.unlink(missing_ok=True)
            flash("Đã lưu sách." if da_luu else "Biểu mẫu này đã được lưu.", "tot")
            return redirect(url_for("quan_ly.danh_sach_sach"))
    danh_muc = [item["danh_muc"] for item in dich_vu.danh_muc()]
    return render_template(
        "quan_ly/sua_sach.html", sach=sach, danh_muc=danh_muc,
        form=request.form, ma_thao_tac=ma_thao_tac, loi_truong=loi_truong,
    )

@bp.post("/sach/<int:ma>/xoa")
def xoa_sach(ma):
    return ngung_ban(ma)


@bp.post("/sach/<int:ma>/ngung-ban")
def ngung_ban(ma):
    return _doi_ban(ma, False, "Đã ngừng bán sách.")


@bp.post("/sach/<int:ma>/mo-ban")
def mo_ban(ma):
    return _doi_ban(ma, True, "Đã mở bán lại sách.")


def _doi_ban(ma, dang_ban, thong_bao):
    try:
        dich_vu.doi_trang_thai_ban(ma, dang_ban)
        flash(thong_bao, "tot")
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
    return redirect(url_for("quan_ly.danh_sach_sach"))

@bp.route("/danh-muc", methods=["GET", "POST"])
def danh_muc():
    if request.method == "POST":
        return thao_tac(
            "danh_muc", dich_vu.luu_danh_muc, request.form.get("ten", ""),
            request.form.get("duong_dan", ""), request.form.get("thu_tu", "0"),
            request.form.get("ma"),
        )
    return render_template("quan_ly/danh_muc.html", danh_muc=dich_vu.danh_muc())

@bp.post("/danh-muc/<int:ma>/xoa")
def xoa_danh_muc(ma):
    return thao_tac("danh_muc", dich_vu.xoa_danh_muc, ma)

@bp.route("/ma-giam-gia", methods=["GET", "POST"])
def ma_giam_gia():
    if request.method == "POST":
        return thao_tac("ma_giam_gia", dich_vu.them_ma_giam_gia, request.form)
    return render_template("quan_ly/ma_giam_gia.html", ma_giam_gia=dich_vu.danh_sach_ma_giam_gia())

@bp.post("/ma-giam-gia/<ma>/bat-tat")
def bat_tat_ma(ma):
    return thao_tac("ma_giam_gia", dich_vu.bat_tat_ma, ma)

@bp.get("/danh-gia")
def danh_gia():
    return render_template("quan_ly/danh_gia.html", danh_gia=dich_vu.danh_sach_danh_gia())

@bp.post("/danh-gia/<int:ma>/an")
def an_danh_gia(ma):
    return thao_tac("danh_gia", dich_vu.doi_an_danh_gia, ma)

@bp.get("/review")
def danh_sach_review():
    loc = request.args.get("trang_thai", "")
    try:
        bai_review = dich_vu.danh_sach_review(loc)
    except LoiNghiepVu as exc:
        abort(400, str(exc))
    return render_template("quan_ly/review.html", bai_review=bai_review, loc=loc)


@bp.route("/review/moi", methods=["GET", "POST"])
def tao_review():
    form = {"ma_sach": request.args.get("ma_sach", type=int), "tac_gia_review": "Nhà Sách Tri Thức"}
    loi_truong = {}
    if request.method == "POST":
        form = {ten: request.form.get(ten, "") for ten in ("tieu_de", "noi_dung", "tac_gia_review")}
        form["ma_sach"] = request.form.get("ma_sach", type=int)
        if not form["ma_sach"] or not 0 < form["ma_sach"] < 2**63:
            loi_truong["ma_sach"] = "Hãy chọn sách."
        else:
            try:
                bai = dich_vu.tao_nhap_review(**form)
            except LoiNghiepVu as exc:
                loi_truong = getattr(exc, "loi_truong", {"ma_sach": str(exc)})
            else:
                flash("Đã tạo review nháp.", "tot")
                return redirect(url_for("quan_ly.sua_review", ma=bai.ma))
    return render_template(
        "quan_ly/tao_review.html", form=form, loi_truong=loi_truong,
        sach_chua_co_review=dich_vu.sach_chua_co_review(),
    ), 400 if loi_truong else 200


@bp.route("/review/<int:ma>/sua", methods=["GET", "POST"])
def sua_review(ma):
    try:
        bai = dich_vu.xem_review(ma)
    except KhongTimThay as exc:
        abort(404, str(exc))
    if request.method == "POST":
        du_lieu = {ten: request.form.get(ten, "") for ten in ("tieu_de", "noi_dung", "tac_gia_review")}
        try:
            dich_vu.sua_review(ma, **du_lieu)
        except LoiNghiepVu as exc:
            flash(str(exc), "loi")
            return render_template(
                "quan_ly/sua_review.html", bai_review=bai, form=du_lieu,
                loi_truong=getattr(exc, "loi_truong", {}),
            ), 400
        flash("Đã lưu nháp review.", "tot")
        return redirect(url_for("quan_ly.danh_sach_review"))
    return render_template("quan_ly/sua_review.html", bai_review=bai, form={})


@bp.post("/review/<int:ma>/duyet")
def duyet_review(ma):
    return thao_tac("danh_sach_review", dich_vu.doi_duyet_review, ma, True)


@bp.post("/review/<int:ma>/bo-duyet")
def bo_duyet_review(ma):
    return thao_tac("danh_sach_review", dich_vu.doi_duyet_review, ma, False)


def thao_tac(dich, ham, *doi_so):
    try:
        ham(*doi_so)
        flash("Đã cập nhật.", "tot")
    except LoiNghiepVu as exc:
        flash(str(exc), "loi")
    return redirect(url_for(f"quan_ly.{dich}"))
