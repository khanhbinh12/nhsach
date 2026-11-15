"""Cửa hàng sách giấy: danh mục, chi tiết, giỏ hàng, thanh toán."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from ...exceptions import BookstoreError
from ...models import Cart, Voucher
from ...services import OrderService
from ..context import current_customer, customer_required, get_store, safe_next
from ..pagination import paginate
from ..session_cart import SessionCart

bp = Blueprint("shop", __name__)
VOUCHER_KEY = "voucher"


def _cart() -> SessionCart:
    return SessionCart(get_store().inventory)


def _current_voucher(cart: Cart) -> Voucher | None:
    """Mã giảm giá khách đã nhập (lưu trong session); tự gỡ nếu không còn hợp lệ với giỏ hiện tại."""
    code = session.get(VOUCHER_KEY)
    if not code or cart.is_empty():
        return None
    try:
        return get_store().vouchers.validate(code, cart.subtotal())
    except BookstoreError as error:
        session.pop(VOUCHER_KEY, None)
        flash(f"{error}. Đã gỡ mã khỏi giỏ hàng.", "info")
        return None


@bp.get("/")
def index():
    store = get_store()
    keyword = request.args.get("q", "").strip()
    category = request.args.get("the-loai") or None
    all_books = store.inventory.catalog()
    return render_template(
        "shop/index.html",
        books=paginate(store.inventory.catalog(keyword, category), per_page=12),
        categories=store.inventory.categories(all_books),
        keyword=keyword,
        category=category,
        ebook_count=len(store.inventory.ebooks()),
        book_count=len(all_books),
        # 3 bìa nổi bật ở đầu trang: ưu tiên sách đã có ảnh bìa thật, còn hàng
        featured=sorted((b for b in all_books if b.can_supply(1)), key=lambda b: not b.cover_image)[:3],
    )


@bp.get("/sach/<product_id>", defaults={"slug": None})
@bp.get("/sach/<product_id>/<slug>")
def book_detail(product_id: str, slug: str | None):
    store = get_store()
    product = store.inventory.find(product_id)
    if product is None or not product.purchasable:
        abort(404)
    if slug != product.slug:
        # Đường dẫn cũ / sai tên (ví dụ sau khi đổi tên sách) → chuyển hẳn sang đường dẫn chuẩn.
        return redirect(url_for(".book_detail", product_id=product.id, slug=product.slug), 301)
    related = [p for p in store.inventory.catalog(category=product.category) if p.id != product.id][:4]
    return render_template("shop/book.html", book=product, related=related)


@bp.get("/gio-hang")
def cart():
    store = get_store()
    cart = _cart().build()
    quote = store.orders.quote(cart, current_customer(), voucher=_current_voucher(cart))
    return render_template("shop/cart.html", cart=cart, quote=quote)


@bp.post("/gio-hang/them")
def add_to_cart():
    product = get_store().inventory.get(request.form.get("product_id", ""))
    _cart().add(product, request.form.get("quantity", "1"))
    flash(f"Đã thêm “{product.title}” vào giỏ hàng.", "success")
    return redirect(safe_next(request.form.get("next"), url_for(".cart")))


@bp.post("/gio-hang/cap-nhat")
def update_cart():
    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 1
    _cart().update(request.form.get("product_id", ""), quantity)
    return redirect(url_for(".cart"))


@bp.post("/gio-hang/xoa")
def remove_from_cart():
    _cart().remove(request.form.get("product_id", ""))
    return redirect(url_for(".cart"))


@bp.post("/gio-hang/ma-giam-gia")
def apply_voucher():
    cart = _cart().build()
    voucher = get_store().vouchers.validate(request.form.get("code", ""), cart.subtotal())
    session[VOUCHER_KEY] = voucher.code
    flash(f"Đã áp dụng mã {voucher.code} ({voucher.value_label}).", "success")
    return redirect(url_for(".cart"))


@bp.post("/gio-hang/bo-ma-giam-gia")
def remove_voucher():
    session.pop(VOUCHER_KEY, None)
    return redirect(url_for(".cart"))


@bp.route("/thanh-toan", methods=["GET", "POST"])
@customer_required
def checkout():
    store = get_store()
    session_cart = _cart()
    cart = session_cart.build()
    if cart.is_empty():
        flash("Giỏ hàng đang trống.", "info")
        return redirect(url_for(".cart"))

    customer = current_customer()
    voucher = _current_voucher(cart)
    form = {
        "contact_phone": request.form.get("contact_phone", customer.phone),
        "shipping_address": request.form.get("shipping_address", ""),
        "payment_method": request.form.get("payment_method", OrderService.PAYMENT_METHODS[0]),
    }
    if request.method == "POST":
        try:
            order = store.place_order(cart, customer=customer, voucher_code=voucher.code if voucher else "", **form)
        except BookstoreError as error:
            flash(str(error), "error")
        else:
            session_cart.clear()
            session.pop(VOUCHER_KEY, None)
            flash("Đặt hàng thành công! Nhà sách sẽ liên hệ xác nhận đơn trong thời gian sớm nhất.", "success")
            return redirect(url_for("accounts.order_detail", order_id=order.id))

    quote = store.orders.quote(cart, customer, voucher=voucher)
    return render_template("shop/checkout.html", cart=cart, quote=quote, form=form,
                           payment_methods=OrderService.PAYMENT_METHODS)
