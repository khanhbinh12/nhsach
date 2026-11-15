"""Kho E-Book: ai cũng xem được danh sách; chỉ hội viên còn hạn mới thấy link Google Drive."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..context import current_account, current_customer, customer_required, get_store
from ..pagination import paginate

bp = Blueprint("library", __name__, url_prefix="/kho-ebook")


@bp.get("/")
def index():
    store = get_store()
    account = current_account()
    customer = current_customer()
    access = None
    if account is not None and account.is_admin:
        access = store.membership.admin_drive_access()
    elif store.membership.has_access(customer):
        access = store.membership.drive_access(customer)

    category = request.args.get("the-loai") or None
    ebooks = store.membership.ebooks()
    return render_template(
        "library/index.html",
        ebooks=paginate([e for e in ebooks if category is None or e.category == category], per_page=24),
        ebook_total=len(ebooks),
        categories=store.inventory.categories(ebooks),
        category=category,
        access=access,
        customer=customer,
        pending=store.membership.pending_request(customer) if customer else None,
    )


@bp.route("/dang-ky-hoi-vien", methods=["GET", "POST"])
@customer_required
def subscribe():
    store = get_store()
    customer = current_customer()
    if request.method == "POST":
        order = store.request_membership(customer)
        flash(f"Đã ghi nhận yêu cầu {order.id}. Gói sẽ được kích hoạt ngay khi nhà sách xác nhận đã nhận tiền.",
              "success")
        return redirect(url_for(".subscribe"))
    return render_template(
        "library/subscribe.html",
        customer=customer,
        pending=store.membership.pending_request(customer),
        has_access=store.membership.has_access(customer),
        transfer_note=f"TRITRI {customer.phone}",
    )
