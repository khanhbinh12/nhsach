"""Tài khoản đăng nhập web.

    Account (trừu tượng)
    ├── CustomerAccount  – gắn với một Customer, mua sách / hội viên
    └── AdminAccount     – quản trị viên

Lớp con tự đăng ký vào ``Account._registry`` qua ``__init_subclass__`` nên khi đọc dữ liệu
chỉ cần ``Account.restore(data)`` là tạo đúng lớp, không cần if/elif.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Mapping

from ..exceptions import AuthenticationError, ValidationError
from .identifiers import DEFAULT_IDS
from .tracking import Trackable
from .validators import optional_text, require_text


class PasswordHasher:
    """Băm mật khẩu bằng PBKDF2-SHA256 có muối ngẫu nhiên – không bao giờ lưu mật khẩu gốc."""

    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 120_000
    MIN_LENGTH = 6

    @classmethod
    def hash(cls, password: str) -> str:
        if len(password or "") < cls.MIN_LENGTH:
            raise ValidationError(f"Mật khẩu phải có ít nhất {cls.MIN_LENGTH} ký tự")
        salt = secrets.token_hex(16)
        digest = cls._digest(password, salt, cls.ITERATIONS)
        return f"{cls.ALGORITHM}${cls.ITERATIONS}${salt}${digest}"

    @classmethod
    def verify(cls, password: str, encoded: str) -> bool:
        try:
            algorithm, iterations, salt, digest = encoded.split("$")
        except ValueError:
            return False
        if algorithm != cls.ALGORITHM:
            return False
        return hmac.compare_digest(cls._digest(password or "", salt, int(iterations)), digest)

    @staticmethod
    def _digest(password: str, salt: str, iterations: int) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations).hex()


class Account(Trackable, ABC):
    """Tài khoản đăng nhập. Lớp con khai báo ``ROLE`` và được tự động đăng ký."""

    ROLE: ClassVar[str] = ""
    ID_PREFIX: ClassVar[str] = "TK"
    DATE_FORMAT: ClassVar[str] = "%Y-%m-%d %H:%M:%S"
    _registry: ClassVar[dict[str, type["Account"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.ROLE:
            Account._registry[cls.ROLE] = cls

    def __init__(
        self,
        *,
        login: str,
        password_hash: str,
        account_id: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._id = optional_text(account_id) or DEFAULT_IDS.new_id(self.ID_PREFIX)
        self._login = require_text(login, "Tên đăng nhập").lower()
        self._password_hash = require_text(password_hash, "Mật khẩu")
        self._created_at = created_at or datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def login(self) -> str:
        return self._login

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def customer_id(self) -> str | None:
        """Mã khách hàng gắn với tài khoản (tài khoản quản trị không có)."""
        return None

    @property
    def display_name(self) -> str:
        """Tên hiển thị mặc định – lớp con có thể ghi đè."""
        return self._login

    # --------------------------------------------------------- đa hình
    @property
    @abstractmethod
    def is_admin(self) -> bool:
        """Có quyền vào trang quản trị hay không."""

    @property
    @abstractmethod
    def role_label(self) -> str:
        """Tên vai trò hiển thị."""

    @property
    @abstractmethod
    def home_endpoint(self) -> str:
        """Trang chuyển tới sau khi đăng nhập (tên endpoint Flask)."""

    # --------------------------------------------------------- mật khẩu
    def check_password(self, password: str) -> bool:
        return PasswordHasher.verify(password, self._password_hash)

    def change_password(self, old_password: str, new_password: str) -> None:
        if not self.check_password(old_password):
            raise AuthenticationError("Mật khẩu hiện tại không đúng")
        self._password_hash = PasswordHasher.hash(new_password)

    # --------------------------------------------------------- lưu trữ
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "role": self.ROLE,
            "login": self._login,
            "password_hash": self._password_hash,
            "created_at": self._created_at.strftime(self.DATE_FORMAT),
        }

    @staticmethod
    def _base_kwargs(data: Mapping[str, Any]) -> dict[str, Any]:
        created = optional_text(data.get("created_at"))
        return {
            "account_id": data.get("id"),
            "login": data.get("login"),
            "password_hash": data.get("password_hash"),
            "created_at": datetime.strptime(created, Account.DATE_FORMAT) if created else None,
        }

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Account":
        """Khôi phục tài khoản của đúng lớp con."""

    @staticmethod
    def restore(data: Mapping[str, Any]) -> "Account":
        role = optional_text(data.get("role")).upper()
        account_cls = Account._registry.get(role)
        if account_cls is None:
            raise ValidationError(f"Loại tài khoản không hỗ trợ: '{role}'")
        return account_cls.from_dict(data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id!r}, login={self._login!r})"


class CustomerAccount(Account):
    """Tài khoản của khách hàng – đăng nhập bằng email."""

    ROLE = "CUSTOMER"

    def __init__(self, *, customer_id: str, **account_kwargs: Any) -> None:
        super().__init__(**account_kwargs)
        self._customer_id = require_text(customer_id, "Mã khách hàng")

    @property
    def customer_id(self) -> str:
        return self._customer_id

    @property
    def is_admin(self) -> bool:
        return False

    @property
    def role_label(self) -> str:
        return "Khách hàng"

    @property
    def home_endpoint(self) -> str:
        return "accounts.profile"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["customer_id"] = self._customer_id
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CustomerAccount":
        return cls(customer_id=data.get("customer_id"), **cls._base_kwargs(data))


class AdminAccount(Account):
    """Tài khoản quản trị viên."""

    ROLE = "ADMIN"

    def __init__(self, *, display_name: str = "Quản trị viên", **account_kwargs: Any) -> None:
        super().__init__(**account_kwargs)
        self._display_name = optional_text(display_name) or "Quản trị viên"

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def is_admin(self) -> bool:
        return True

    @property
    def role_label(self) -> str:
        return "Quản trị viên"

    @property
    def home_endpoint(self) -> str:
        return "admin.dashboard"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["display_name"] = self._display_name
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdminAccount":
        return cls(display_name=data.get("display_name", ""), **cls._base_kwargs(data))
