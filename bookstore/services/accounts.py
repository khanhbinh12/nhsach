"""Dịch vụ tài khoản: đăng ký, đăng nhập, đổi mật khẩu."""

from __future__ import annotations

from typing import Iterable

from ..exceptions import AuthenticationError, NotFoundError, ValidationError
from ..models import (
    DEFAULT_IDS,
    Account,
    AdminAccount,
    Customer,
    CustomerAccount,
    CustomerFactory,
    IdGenerator,
    PasswordHasher,
)
from ..models.validators import require_text
from .customers import CustomerService


class AccountService:
    def __init__(self, customers: CustomerService, accounts: Iterable[Account] = (),
                 ids: IdGenerator = DEFAULT_IDS) -> None:
        self._customers = customers
        self._ids = ids
        self._accounts: dict[str, Account] = {}
        for account in accounts:
            self.add(account)

    def find(self, account_id: str | None) -> Account | None:
        return self._accounts.get(account_id or "")

    def get(self, account_id: str) -> Account:
        account = self.find(account_id)
        if account is None:
            raise NotFoundError("Không tìm thấy tài khoản")
        return account

    def new_id(self) -> str:
        """Mã tài khoản chưa dùng."""
        return self._ids.new_id(Account.ID_PREFIX, self._accounts.__contains__)

    def find_by_login(self, login: str) -> Account | None:
        key = (login or "").strip().lower()
        return next((a for a in self._accounts.values() if a.login == key), None)

    def find_by_customer(self, customer_id: str) -> Account | None:
        return next((a for a in self._accounts.values() if a.customer_id == customer_id), None)

    def all(self) -> list[Account]:
        return list(self._accounts.values())

    def customer_of(self, account: Account | None) -> Customer | None:
        if account is None:
            return None
        return self._customers.find(account.customer_id)

    def add(self, account: Account) -> Account:
        if account.id in self._accounts:
            raise ValidationError(f"Mã tài khoản '{account.id}' đã tồn tại")
        if self.find_by_login(account.login):
            raise ValidationError(f"Tài khoản '{account.login}' đã tồn tại")
        self._accounts[account.id] = account
        return account

    def register_customer(self, *, name: str, phone: str, email: str, password: str) -> CustomerAccount:
        """Tạo đồng thời Customer và CustomerAccount – kiểm tra hết rồi mới lưu."""
        email = require_text(email, "Email")
        customer = CustomerFactory.create(name=name, phone=phone, email=email, customer_id=self._customers.new_id())
        password_hash = PasswordHasher.hash(password)
        account = CustomerAccount(login=customer.email, password_hash=password_hash, customer_id=customer.id,
                                  account_id=self.new_id())
        self._customers.ensure_unique(customer)
        if self.find_by_login(account.login):
            raise ValidationError(f"Email {account.login} đã được đăng ký")
        self._customers.add(customer)
        return self.add(account)  # type: ignore[return-value]

    def create_admin(self, *, login: str, password: str, display_name: str = "Quản trị viên") -> AdminAccount:
        admin = AdminAccount(login=login, password_hash=PasswordHasher.hash(password), display_name=display_name,
                             account_id=self.new_id())
        return self.add(admin)  # type: ignore[return-value]

    def authenticate(self, login: str, password: str) -> Account:
        """Đăng nhập bằng email / tên đăng nhập, hoặc số điện thoại của khách."""
        account = self.find_by_login(login)
        if account is None:
            customer = self._customers.find_by_identifier(login)
            account = self.find_by_customer(customer.id) if customer else None
        if account is None or not account.check_password(password):
            raise AuthenticationError("Sai tài khoản hoặc mật khẩu")
        return account

    def change_password(self, account_id: str, old_password: str, new_password: str) -> Account:
        account = self.get(account_id)
        account.change_password(old_password, new_password)
        return account
