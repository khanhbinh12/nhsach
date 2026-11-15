"""Facade ``Bookstore``: điểm truy cập duy nhất của tầng web vào tầng nghiệp vụ.

- Đọc dữ liệu: qua các thuộc tính ``inventory``, ``customers``, ``accounts``, ``orders``,
  ``vouchers``, ``membership``, ``ads``, ``reports``.
- Thay đổi dữ liệu: qua các phương thức gắn ``@command``; mỗi lệnh chạy trong khóa (an toàn khi
  nhiều request cùng lúc) và thành công thì tự lưu xuống ``DataStorage``.
"""

from __future__ import annotations

import functools
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping, TypeVar

from ..exceptions import AuthenticationError, BookstoreError, DataCorruptedError, UnsupportedOperationError
from ..models import (
    Account,
    AdLedger,
    AdSession,
    AdSettings,
    Cart,
    Customer,
    CustomerAccount,
    CustomerFactory,
    DiscountRegistry,
    EBookVault,
    Order,
    Product,
    ProductFactory,
    VIPTier,
    Voucher,
)
from ..storage import DataStorage
from .accounts import AccountService
from .ads import AdService
from .customers import CustomerService
from .inventory import InventoryService
from .login_throttle import LoginThrottle
from .media import CoverImageStore
from .membership import MembershipService
from .orders import OrderService
from .reports import ReportService
from .unit_of_work import UnitOfWork
from .vouchers import VoucherService

F = TypeVar("F", bound=Callable[..., Any])

DATA_VERSION = 4
SUPPORTED_VERSIONS = {3, 4}  # bản 3 chưa có voucher / ảnh bìa – đọc được, lưu lại thành bản 4
COLLECTION_KEYS = {"products": "id", "customers": "id", "accounts": "id", "orders": "id", "vouchers": "code"}


def command(method: F) -> F:
    """Đánh dấu một thao tác ghi: chạy trong khóa và lưu dữ liệu khi thành công."""

    @functools.wraps(method)
    def wrapper(self: "Bookstore", *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            result = method(self, *args, **kwargs)
            self.save()
            return result

    return wrapper  # type: ignore[return-value]


class Bookstore:
    def __init__(
        self,
        storage: DataStorage,
        *,
        clock: Callable[[], datetime] = datetime.now,
        media: CoverImageStore | None = None,
    ) -> None:
        self._storage = storage
        self._clock = clock
        self._media = media
        self._lock = threading.RLock()
        self._discounts = DiscountRegistry.default()
        # Chống dò mật khẩu: theo tài khoản (5 lần sai/15 phút) và theo địa chỉ IP (20 lần sai/15 phút).
        self._account_throttle = LoginThrottle(max_failures=5, window=timedelta(minutes=15),
                                               lockout=timedelta(minutes=15), clock=clock)
        self._ip_throttle = LoginThrottle(max_failures=20, window=timedelta(minutes=15),
                                          lockout=timedelta(minutes=15), clock=clock)
        data = storage.load()
        if data is None:
            self.reset_sample_data()
        else:
            self._restore(data)

    # ------------------------------------------------------- khởi tạo & lưu
    def _wire(self, *, products=(), customers=(), accounts=(), orders=(), vouchers=(), vault=None,
              ad_settings=None, ad_ledger=None) -> None:
        self._inventory = InventoryService(products)
        self._customers = CustomerService(customers)
        self._accounts = AccountService(self._customers, accounts)
        self._vouchers = VoucherService(vouchers, self._clock)
        self._orders = OrderService(self._inventory, self._discounts, self._vouchers, orders, self._clock)
        self._membership = MembershipService(
            vault or EBookVault(), self._customers, self._orders, self._inventory, self._clock
        )
        self._ads = AdService(ad_settings or AdSettings(), ad_ledger or AdLedger(), self._clock)
        self._reports = ReportService(self._inventory, self._customers, self._orders, self._membership, self._ads)
        # Observer: các dịch vụ tự phản ứng khi đơn được hoàn tất / hủy.
        for listener in (self._inventory, self._customers, self._membership, self._vouchers):
            self._orders.add_listener(listener)
        # Unit of Work: sau mỗi lệnh chỉ ghi các đối tượng đã thay đổi.
        self._unit_of_work = UnitOfWork(
            collections={
                "products": self._inventory.all,
                "customers": self._customers.all,
                "accounts": self._accounts.all,
                "orders": self._orders.stored,
                "vouchers": self._vouchers.all,
            },
            key_fields=COLLECTION_KEYS,
            settings=self._settings,
            snapshot=self.to_dict,
        )

    def _settings(self) -> dict[str, Any]:
        """Cấu hình nhỏ, luôn được ghi cùng mỗi lệnh."""
        return {
            "version": DATA_VERSION,
            "vault": self._membership.vault.to_dict(),
            "ad_settings": self._ads.settings.to_dict(),
            "ad_views": self._ads.ledger.to_dict(),
        }

    def _restore(self, data: Mapping[str, Any]) -> None:
        if data.get("version") not in SUPPORTED_VERSIONS:
            raise DataCorruptedError(f"Phiên bản dữ liệu không hỗ trợ: {data.get('version')!r}")
        try:
            self._wire(
                products=[ProductFactory.create(item) for item in data.get("products", [])],
                customers=[CustomerFactory.from_dict(item) for item in data.get("customers", [])],
                accounts=[Account.restore(item) for item in data.get("accounts", [])],
                orders=[Order.from_dict(item) for item in data.get("orders", [])],
                vouchers=[Voucher.restore(item) for item in data.get("vouchers", [])],
                vault=EBookVault.from_dict(data.get("vault") or {}),
                ad_settings=AdSettings.from_dict(data.get("ad_settings") or {}),
                ad_ledger=AdLedger.from_dict(data.get("ad_views") or {}),
            )
        except (BookstoreError, KeyError, TypeError, ValueError) as error:
            raise DataCorruptedError(f"Dữ liệu không hợp lệ: {error}") from error
        if data.get("version") == DATA_VERSION:
            self._unit_of_work.mark_clean()  # vừa đọc lên, chưa có gì thay đổi
        # Dữ liệu phiên bản cũ: để nguyên trạng thái "đã thay đổi" → lệnh ghi đầu tiên sẽ nâng cấp toàn bộ.

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._settings(),
            "products": [p.to_dict() for p in self._inventory.all()],
            "customers": [c.to_dict() for c in self._customers.all()],
            "accounts": [a.to_dict() for a in self._accounts.all()],
            "orders": [o.to_dict() for o in self._orders.stored()],
            "vouchers": [v.to_dict() for v in self._vouchers.all()],
        }

    def save(self) -> None:
        with self._lock:
            self._unit_of_work.commit(self._storage)

    def reset_sample_data(self) -> None:
        from .seed import SampleDataSeeder  # import trễ để tránh vòng lặp import

        with self._lock:
            self._wire()
            SampleDataSeeder(self).populate()
            # Dựng lại toàn bộ dữ liệu → thay thế hẳn (không ghi tăng dần) để thứ tự lưu khớp với bộ nhớ.
            self._storage.save(self.to_dict())
            self._unit_of_work.mark_clean()

    def now(self) -> datetime:
        return self._clock()

    # ------------------------------------------------------ truy cập chỉ đọc
    @property
    def inventory(self) -> InventoryService:
        return self._inventory

    @property
    def customers(self) -> CustomerService:
        return self._customers

    @property
    def accounts(self) -> AccountService:
        return self._accounts

    @property
    def orders(self) -> OrderService:
        return self._orders

    @property
    def vouchers(self) -> VoucherService:
        return self._vouchers

    @property
    def membership(self) -> MembershipService:
        return self._membership

    @property
    def ads(self) -> AdService:
        return self._ads

    @property
    def reports(self) -> ReportService:
        return self._reports

    @property
    def discounts(self) -> DiscountRegistry:
        return self._discounts

    @property
    def vault(self) -> EBookVault:
        return self._membership.vault

    @property
    def media(self) -> CoverImageStore | None:
        return self._media

    # ------------------------------------------------------ tài khoản
    def authenticate(self, login: str, password: str, client_ip: str = "") -> Account:
        """Đăng nhập có giới hạn số lần sai (báo AuthenticationError khi sai hoặc đang bị tạm khóa)."""
        account_key = f"login:{(login or '').strip().lower()}"
        ip_key = f"ip:{client_ip}"
        self._account_throttle.ensure_allowed(account_key)
        if client_ip:
            self._ip_throttle.ensure_allowed(ip_key)
        try:
            account = self._accounts.authenticate(login, password)
        except AuthenticationError:
            self._account_throttle.record_failure(account_key)
            if client_ip:
                self._ip_throttle.record_failure(ip_key)
            raise
        self._account_throttle.reset(account_key)
        return account

    @command
    def register_customer(self, *, name: str, phone: str, email: str, password: str) -> CustomerAccount:
        return self._accounts.register_customer(name=name, phone=phone, email=email, password=password)

    @command
    def change_password(self, account_id: str, old_password: str, new_password: str) -> Account:
        return self._accounts.change_password(account_id, old_password, new_password)

    # ------------------------------------------------------ mua sách
    @command
    def place_order(self, cart: Cart, *, customer: Customer, payment_method: str, shipping_address: str,
                    contact_phone: str = "", voucher_code: str = "") -> Order:
        return self._orders.place_order(cart, customer=customer, payment_method=payment_method,
                                        shipping_address=shipping_address, contact_phone=contact_phone,
                                        voucher_code=voucher_code)

    @command
    def ship_order(self, order_id: str) -> Order:
        return self._orders.ship(order_id)

    @command
    def complete_order(self, order_id: str) -> Order:
        return self._orders.complete(order_id)

    @command
    def cancel_order(self, order_id: str) -> Order:
        return self._orders.cancel(order_id)

    @command
    def cancel_own_order(self, customer: Customer, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order.customer_id != customer.id:
            raise BookstoreError("Bạn không thể hủy đơn của người khác")
        if not order.customer_can_cancel:
            raise BookstoreError(f"Đơn đang ở trạng thái '{order.status.label}', vui lòng liên hệ nhà sách để hủy")
        return self._orders.cancel(order_id)

    # ------------------------------------------------------ mã giảm giá
    @command
    def create_voucher(self, form: Mapping[str, Any]) -> Voucher:
        return self._vouchers.create(form)

    @command
    def set_voucher_active(self, code: str, active: bool) -> Voucher:
        return self._vouchers.set_active(code, active)

    @command
    def delete_voucher(self, code: str) -> Voucher:
        return self._vouchers.remove(code)

    # ------------------------------------------------------ hội viên E-Book
    @command
    def request_membership(self, customer: Customer) -> Order:
        return self._membership.request(customer)

    @command
    def grant_membership(self, customer_id: str) -> Customer:
        return self._membership.grant(customer_id)

    @command
    def revoke_membership(self, customer_id: str) -> Customer:
        return self._membership.revoke(customer_id)

    @command
    def update_vault(self, changes: Mapping[str, Any]) -> EBookVault:
        return self._membership.update_vault(changes)

    # ------------------------------------------------------ quảng cáo ủng hộ
    def start_ad(self, viewer_id: str) -> AdSession:
        with self._lock:
            return self._ads.start(viewer_id)

    @command
    def complete_ad(self, token: str | None, viewer_id: str) -> int:
        return self._ads.complete(token, viewer_id)

    @command
    def update_ad_settings(self, changes: Mapping[str, Any]) -> AdSettings:
        return self._ads.update_settings(changes)

    # ------------------------------------------------------ quản lý kho & khách
    @command
    def create_product(self, data: Mapping[str, Any]) -> Product:
        return self._inventory.create(data)

    @command
    def update_product(self, product_id: str, changes: Mapping[str, Any]) -> Product:
        return self._inventory.update(product_id, changes)

    @command
    def delete_product(self, product_id: str) -> Product:
        product = self._inventory.remove(product_id)
        if self._media is not None:
            self._media.delete(product.cover_image)
        return product

    @command
    def restock(self, product_id: str, quantity: int | str) -> Product:
        return self._inventory.restock(product_id, quantity)

    @command
    def set_cover(self, product_id: str, filename: str, data: bytes) -> Product:
        if self._media is None:
            raise UnsupportedOperationError("Chưa cấu hình thư mục lưu ảnh bìa")
        product = self._inventory.get(product_id)
        old_image = product.cover_image
        product.cover_image = self._media.save(product.id, filename, data)
        self._media.delete(old_image)
        return product

    @command
    def remove_cover(self, product_id: str) -> Product:
        product = self._inventory.get(product_id)
        if self._media is not None:
            self._media.delete(product.cover_image)
        product.cover_image = ""
        return product

    @command
    def promote_to_vip(self, customer_id: str, tier: VIPTier | str = VIPTier.BRONZE) -> Customer:
        return self._customers.promote_to_vip(customer_id, tier)
