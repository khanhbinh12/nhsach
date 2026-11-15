"""Đăng ký, đăng nhập, trang tài khoản và đơn hàng của khách."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from ...exceptions import BookstoreError
from ...services.seed import ADMIN_LOGIN, ADMIN_PASSWORD, DEMO_PASSWORD
from ..context import (
    current_account,
    current_customer,
    customer_required,
    get_store,
    login_required,
    login_user,
    logout_user,
    safe_next,
)
from ..pagination import paginate

bp = Blueprint("accounts", __name__, url_prefix="/tai-khoan")


@bp.route("/dang-nhap", methods=["GET", "POST"])
def login():
    login_value = request.form.get("login", "")
    if request.method == "POST":
        client_ip = request.remote_addr or ""
        try:
            account = get_store().authenticate(login_value, request.form.get("password", ""), client_ip)
        except BookstoreError as error:
            current_app.logger.warning("Đăng nhập thất bại: tài khoản=%r ip=%s (%s)", login_value, client_ip, error)
            flash(str(error), "error")
        else:
            current_app.logger.info("Đăng nhập: %s (%s) ip=%s", account.login, account.role_label, client_ip)
            login_user(account)
            flash("Đăng nhập thành công.", "success")
            # Đa hình: mỗi loại tài khoản tự biết trang chủ của mình.
            return redirect(safe_next(request.args.get("next"), url_for(account.home_endpoint)))
    demo = {"admin": (ADMIN_LOGIN, ADMIN_PASSWORD), "customer": ("nam.nt@example.com", DEMO_PASSWORD)}
    return render_template("accounts/login.html", login_value=login_value, demo=demo)


@bp.route("/dang-ky", methods=["GET", "POST"])
def register():
    form = {key: request.form.get(key, "").strip() for key in ("name", "phone", "email")}
    if request.method == "POST":
        password = request.form.get("password", "")
        if password != request.form.get("confirm_password", ""):
            flash("Mật khẩu nhập lại không khớp.", "error")
        else:
            try:
                account = get_store().register_customer(password=password, **form)
            except BookstoreError as error:
                flash(str(error), "error")
            else:
                login_user(account)
                flash("Tạo tài khoản thành công. Chào mừng bạn đến với Nhà Sách Trí Tri!", "success")
                return redirect(safe_next(request.args.get("next"), url_for(".profile")))
    return render_template("accounts/register.html", form=form)


@bp.post("/dang-xuat")
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("shop.index"))


@bp.get("/")
@login_required
def profile():
    account = current_account()
    customer = current_customer()
    if customer is None:
        return redirect(url_for(account.home_endpoint))
    store = get_store()
    return render_template(
        "accounts/profile.html",
        customer=customer,
        orders=paginate(store.orders.by_customer(customer.id), per_page=10),
        has_access=store.membership.has_access(customer),
        pending_membership=store.membership.pending_request(customer),
    )


@bp.get("/don-hang/<order_id>")
@customer_required
def order_detail(order_id: str):
    order = get_store().orders.find(order_id)
    if order is None or order.customer_id != current_customer().id:
        abort(404)
    return render_template("accounts/order.html", order=order)


@bp.post("/don-hang/<order_id>/huy")
@customer_required
def cancel_order(order_id: str):
    get_store().cancel_own_order(current_customer(), order_id)
    flash(f"Đã hủy đơn {order_id}.", "info")
    return redirect(url_for(".order_detail", order_id=order_id))


@bp.post("/doi-mat-khau")
@login_required
def change_password():
    new_password = request.form.get("new_password", "")
    if new_password != request.form.get("confirm_password", ""):
        flash("Mật khẩu mới nhập lại không khớp.", "error")
    else:
        get_store().change_password(current_account().id, request.form.get("old_password", ""), new_password)
        flash("Đã đổi mật khẩu.", "success")
    return redirect(url_for(".profile"))
