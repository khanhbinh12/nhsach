"""Trang quản trị: tổng quan, duyệt đơn, quản lý sách, khách hàng, cấu hình."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from ...exceptions import BookstoreError
from ...models import OrderAction, OrderStatus, ProductFormat, VIPTier, Voucher
from ..context import current_account, get_store, logout_user, require_admin
from ..forms import ProductForm
from ..pagination import paginate

bp = Blueprint("admin", __name__, url_prefix="/quan-tri")
bp.before_request(require_admin)


@bp.after_request
def audit_log(response):
    """Nhật ký quản trị: mọi thao tác ghi (POST) đều được lưu lại – ai làm, làm gì, kết quả ra sao."""
    account = current_account()
    if request.method == "POST" and account is not None and account.is_admin:
        current_app.logger.info("Quản trị %s: POST %s -> %s", account.login, request.path, response.status_code)
    return response

VAULT_FIELDS = ("title", "folder_url", "membership_fee", "duration_days", "description", "bank_info")
AD_FIELDS = ("duration_seconds", "revenue_per_view")


def _back(default_endpoint: str):
    return redirect(request.referrer or url_for(default_endpoint))


# ------------------------------------------------------------------ tổng quan
@bp.get("/")
def dashboard():
    store = get_store()
    return render_template(
        "admin/dashboard.html",
        summary=store.reports.summary(),
        top_sellers=store.reports.top_sellers(),
        categories=store.reports.revenue_by_category(),
        low_stock=store.inventory.low_stock(),
        open_orders=store.orders.by_status(OrderStatus.PENDING, OrderStatus.SHIPPING)[:6],
        ad_days=store.reports.ad_views_recent(store.now().date()),
    )


# ------------------------------------------------------------------ đơn hàng
@bp.get("/don-hang")
def orders():
    raw_status = request.args.get("trang-thai", "")
    status = OrderStatus(raw_status) if raw_status in OrderStatus.__members__ else None
    return render_template("admin/orders.html", orders=paginate(get_store().orders.by_status(status), 25),
                           status=status,
                           statuses=list(OrderStatus))


@bp.post("/don-hang/<order_id>/<action>")
def order_action(order_id: str, action: str):
    """Một route cho mọi thao tác; trạng thái hiện tại của đơn (State) quyết định thao tác có hợp lệ không."""
    try:
        chosen = OrderAction(action)
    except ValueError:
        abort(404)
    store = get_store()
    handlers = {
        OrderAction.SHIP: (store.ship_order, "Đơn {} đã chuyển sang Đang giao."),
        OrderAction.COMPLETE: (store.complete_order, "Đơn {} đã hoàn tất."),
        OrderAction.CANCEL: (store.cancel_order, "Đã hủy đơn {}."),
    }
    handler, message = handlers[chosen]
    order = handler(order_id)
    flash(message.format(order.id), "success")
    return _back(".orders")


# ------------------------------------------------------------------ mã giảm giá
@bp.route("/ma-giam-gia", methods=["GET", "POST"])
def vouchers():
    store = get_store()
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        try:
            voucher = store.create_voucher(request.form)
        except BookstoreError as error:
            flash(str(error), "error")
        else:
            flash(f"Đã tạo mã {voucher.code}.", "success")
            return redirect(url_for(".vouchers"))
    return render_template("admin/vouchers.html", vouchers=store.vouchers.all(), kinds=Voucher.kinds(), form=form,
                           today=store.now().date())


@bp.post("/ma-giam-gia/<code>/bat-tat")
def toggle_voucher(code: str):
    store = get_store()
    voucher = store.set_voucher_active(code, not store.vouchers.get(code).active)
    flash(f"Mã {voucher.code} {'đã bật' if voucher.active else 'đã tạm ngưng'}.", "info")
    return redirect(url_for(".vouchers"))


@bp.post("/ma-giam-gia/<code>/xoa")
def delete_voucher(code: str):
    voucher = get_store().delete_voucher(code)
    flash(f"Đã xóa mã {voucher.code}. Đơn hàng cũ dùng mã này vẫn giữ nguyên số tiền.", "info")
    return redirect(url_for(".vouchers"))


# ------------------------------------------------------------------ sách
def _save_cover(product_id: str) -> bool:
    """Xử lý ảnh bìa gửi kèm form; trả về False nếu ảnh lỗi (sách vẫn đã được lưu)."""
    store = get_store()
    upload = request.files.get("cover")
    try:
        if request.form.get("remove_cover"):
            store.remove_cover(product_id)
        if upload is not None and upload.filename:
            store.set_cover(product_id, upload.filename, upload.read())
    except BookstoreError as error:
        flash(f"Đã lưu thông tin sách nhưng ảnh bìa chưa được cập nhật: {error}", "error")
        return False
    return True
@bp.get("/sach")
def products():
    store = get_store()
    raw_format = request.args.get("dinh-dang", "")
    fmt = ProductFormat(raw_format) if raw_format in ("PHYSICAL", "EBOOK") else None
    keyword = request.args.get("q", "")
    return render_template("admin/products.html", products=paginate(store.inventory.search(keyword, fmt), 25),
                           fmt=fmt,
                           keyword=keyword, threshold=store.inventory.LOW_STOCK_THRESHOLD)


@bp.route("/sach/them/<fmt>", methods=["GET", "POST"])
def create_product(fmt: str):
    try:
        form_cls = ProductForm.for_format(ProductFormat(fmt.upper()))
    except (ValueError, KeyError):
        abort(404)
    form = form_cls()
    if request.method == "POST":
        form = form_cls(data=request.form)
        try:
            product = get_store().create_product(form.submitted_data(request.form))
        except BookstoreError as error:
            flash(str(error), "error")
        else:
            if not _save_cover(product.id):
                return redirect(url_for(".edit_product", product_id=product.id))
            flash(f"Đã thêm “{product.title}”.", "success")
            return redirect(url_for(".products"))
    return render_template("admin/product_form.html", form=form)


@bp.route("/sach/<product_id>/sua", methods=["GET", "POST"])
def edit_product(product_id: str):
    store = get_store()
    product = store.inventory.find(product_id)
    if product is None:
        abort(404)
    form = ProductForm.for_product(product)
    if request.method == "POST":
        form = type(form)(product, data=request.form)
        try:
            store.update_product(product_id, form.submitted_data(request.form))
        except BookstoreError as error:
            flash(str(error), "error")
        else:
            if not _save_cover(product_id):
                return redirect(url_for(".edit_product", product_id=product_id))
            flash(f"Đã cập nhật “{product.title}”.", "success")
            return redirect(url_for(".products"))
    return render_template("admin/product_form.html", form=form)


@bp.post("/sach/<product_id>/xoa")
def delete_product(product_id: str):
    product = get_store().delete_product(product_id)
    flash(f"Đã xóa “{product.title}”. Các đơn hàng cũ vẫn được giữ nguyên.", "info")
    return redirect(url_for(".products"))


@bp.post("/sach/<product_id>/nhap-kho")
def restock(product_id: str):
    quantity = request.form.get("quantity", "")
    product = get_store().restock(product_id, quantity)
    flash(f"Đã nhập thêm {quantity} cuốn “{product.title}” (tồn kho: {product.stock_label()}).", "success")
    return _back(".products")


# ------------------------------------------------------------------ khách hàng
@bp.get("/khach-hang")
def customers():
    store = get_store()
    keyword = request.args.get("q", "")
    vip_tiers = [t for t in VIPTier if t is not VIPTier.STANDARD]
    return render_template("admin/customers.html", customers=paginate(store.customers.search(keyword), 25),
                           keyword=keyword,
                           vip_tiers=vip_tiers, now=store.now())


@bp.post("/khach-hang/<customer_id>/tang-hoi-vien")
def grant_membership(customer_id: str):
    customer = get_store().grant_membership(customer_id)
    flash(f"Đã tặng/gia hạn hội viên cho {customer.name}.", "success")
    return _back(".customers")


@bp.post("/khach-hang/<customer_id>/thu-hoi-hoi-vien")
def revoke_membership(customer_id: str):
    customer = get_store().revoke_membership(customer_id)
    flash(f"Đã thu hồi hội viên của {customer.name}.", "info")
    return _back(".customers")


@bp.post("/khach-hang/<customer_id>/nang-vip")
def promote_vip(customer_id: str):
    customer = get_store().promote_to_vip(customer_id, request.form.get("tier", VIPTier.BRONZE.value))
    flash(f"{customer.name} đã trở thành khách VIP hạng {customer.tier.label}.", "success")
    return _back(".customers")


# ------------------------------------------------------------------ cấu hình
@bp.route("/cau-hinh", methods=["GET", "POST"])
def settings():
    store = get_store()
    if request.method == "POST":
        if request.form.get("section") == "ads":
            store.update_ad_settings({key: request.form.get(key, "") for key in AD_FIELDS})
        else:
            store.update_vault({key: request.form.get(key, "") for key in VAULT_FIELDS})
        flash("Đã lưu cấu hình.", "success")
        return redirect(url_for(".settings"))
    return render_template("admin/settings.html", vault=store.vault, ad_settings=store.ads.settings)


@bp.post("/dat-lai-du-lieu")
def reset_data():
    get_store().reset_sample_data()
    logout_user()
    flash("Đã đặt lại dữ liệu mẫu. Vui lòng đăng nhập lại (admin / admin123).", "info")
    return redirect(url_for("accounts.login"))
