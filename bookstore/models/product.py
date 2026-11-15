"""Cây kế thừa sản phẩm.

    Product (trừu tượng)
    ├── Book (trừu tượng)
    │   ├── PhysicalBook   – sách giấy: bán trên web, có tồn kho, phí ship theo cân nặng
    │   └── EBook          – sách điện tử trong Kho Drive, chỉ dành cho hội viên (không bán lẻ)
    └── MembershipPlan     – gói hội viên Kho E-Book

Đa hình: ``purchasable``, ``shipping_fee()``, ``can_supply()``, ``take_from_stock()``,
``return_to_stock()``, ``restock()``, ``is_low_stock()``, ``extra_info()``, ``to_dict()`` được mỗi
lớp hiện thực theo cách riêng, nên lớp dịch vụ không cần ``isinstance()`` để phân biệt loại sách.

``ProductFactory`` (Factory + Registry) tạo đúng lớp con từ dữ liệu, không dùng chuỗi if/elif.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Callable, ClassVar, Mapping

from ..exceptions import OutOfStockError, UnsupportedOperationError, ValidationError
from .enums import ProductFormat
from .identifiers import DEFAULT_IDS
from .text import slugify
from .tracking import Trackable
from .validators import optional_text, require_text, to_float, to_int


class Product(Trackable, ABC):
    """Lớp trừu tượng: mọi mặt hàng có thể bán trong nhà sách."""

    ID_PREFIX: ClassVar[str] = "SP"
    #: Các trường được phép sửa qua ``apply_changes`` – lớp con mở rộng tuple này.
    EDITABLE_FIELDS: ClassVar[tuple[str, ...]] = ("title", "price", "category")

    def __init__(self, *, product_id: str | None, title: str, price: float, category: str,
                 cover_image: str = "") -> None:
        self._id = optional_text(product_id) or DEFAULT_IDS.new_id(self.ID_PREFIX)
        self.title = title
        self.price = price
        self.category = category
        self.cover_image = cover_image

    # ------------------------------------------------------------------ đóng gói
    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = require_text(value, "Tên sản phẩm")

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        self._price = to_float(value, "Giá bán")

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = optional_text(value) or "Tổng hợp"

    @property
    def slug(self) -> str:
        """Phần tên trong đường dẫn thân thiện, ví dụ 'lap-trinh-huong-doi-tuong'."""
        return slugify(self._title)

    @property
    def cover_image(self) -> str:
        """Tên file ảnh bìa đã tải lên (rỗng = dùng bìa vẽ tự động)."""
        return self._cover_image

    @cover_image.setter
    def cover_image(self, value: str) -> None:
        name = optional_text(value)
        if name and (name != name.replace("/", "").replace("\\", "") or name.startswith(".")):
            raise ValidationError("Tên file ảnh bìa không hợp lệ")
        self._cover_image = name

    # ------------------------------------------------------------- trừu tượng
    @property
    @abstractmethod
    def format(self) -> ProductFormat:
        """Định dạng sản phẩm."""

    @abstractmethod
    def shipping_fee(self) -> float:
        """Phí vận chuyển của sản phẩm khi giao hàng."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Product":
        """Khôi phục đối tượng từ dữ liệu đã lưu."""

    @property
    def purchasable(self) -> bool:
        """Có được cho vào giỏ hàng để bán lẻ hay không."""
        return True

    # ------------------------- tồn kho: mặc định là sản phẩm số, không giới hạn
    @property
    def tracks_stock(self) -> bool:
        return False

    @property
    def stock(self) -> int | None:
        return None

    def stock_label(self) -> str:
        return "Không giới hạn"

    def can_supply(self, quantity: int) -> bool:
        return quantity > 0

    def take_from_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Số lượng phải lớn hơn 0")

    def return_to_stock(self, quantity: int) -> None:
        """Hoàn lại hàng khi đơn bị hủy – sản phẩm số không cần làm gì."""

    def restock(self, quantity: int) -> None:
        raise UnsupportedOperationError(f"'{self.title}' là sản phẩm số, không cần nhập kho")

    def is_low_stock(self, threshold: int) -> bool:
        return False

    # ---------------------------------------------------- hiển thị & lưu trữ
    def byline(self) -> str:
        """Dòng mô tả ngắn (tác giả…) – lớp con ghi đè nếu có."""
        return ""

    def extra_info(self) -> dict[str, str]:
        """Thông tin riêng của từng loại sản phẩm để hiển thị."""
        return {}

    def apply_changes(self, data: Mapping[str, Any]) -> None:
        """Cập nhật các trường cho phép sửa; mỗi setter tự kiểm tra hợp lệ."""
        for key in self.EDITABLE_FIELDS:
            if key in data:
                setattr(self, key, data[key])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "format": self.format.value,
            "title": self._title,
            "price": self._price,
            "category": self._category,
            "cover_image": self._cover_image,
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id!r}, title={self._title!r})"


class Book(Product):
    """Lớp trừu tượng trung gian: thông tin xuất bản chung của mọi loại sách."""

    ID_PREFIX = "BK"
    EDITABLE_FIELDS = Product.EDITABLE_FIELDS + ("author", "publisher", "publish_year", "description")

    def __init__(
        self,
        *,
        product_id: str | None = None,
        title: str,
        price: float | str = 0,
        category: str = "",
        author: str,
        isbn: str = "",
        publisher: str = "",
        publish_year: int | str | None = None,
        description: str = "",
        cover_image: str = "",
    ) -> None:
        super().__init__(product_id=product_id, title=title, price=price, category=category,
                         cover_image=cover_image)
        self.author = author
        self._isbn = optional_text(isbn)
        self.publisher = publisher
        self.publish_year = date.today().year if publish_year in (None, "") else publish_year
        self.description = description

    @property
    def author(self) -> str:
        return self._author

    @author.setter
    def author(self, value: str) -> None:
        self._author = require_text(value, "Tác giả")

    @property
    def isbn(self) -> str:
        """ISBN là định danh xuất bản nên chỉ đọc."""
        return self._isbn

    @property
    def publisher(self) -> str:
        return self._publisher

    @publisher.setter
    def publisher(self, value: str) -> None:
        self._publisher = optional_text(value)

    @property
    def publish_year(self) -> int:
        return self._publish_year

    @publish_year.setter
    def publish_year(self, value: int | str) -> None:
        year = to_int(value, "Năm xuất bản", minimum=1000)
        if year > date.today().year + 1:
            raise ValidationError(f"Năm xuất bản {year} nằm trong tương lai")
        self._publish_year = year

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = optional_text(value)

    def byline(self) -> str:
        return self._author

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            author=self._author,
            isbn=self._isbn,
            publisher=self._publisher,
            publish_year=self._publish_year,
            description=self._description,
        )
        return data

    @staticmethod
    def _book_kwargs(data: Mapping[str, Any]) -> dict[str, Any]:
        """Trích các tham số chung của Book từ dữ liệu – dùng lại ở mọi lớp con."""
        return {
            "product_id": data.get("id"),
            "title": data.get("title"),
            "price": data.get("price", 0),
            "category": data.get("category", ""),
            "author": data.get("author"),
            "isbn": data.get("isbn", ""),
            "publisher": data.get("publisher", ""),
            "publish_year": data.get("publish_year"),
            "description": data.get("description", ""),
            "cover_image": data.get("cover_image", ""),
        }


class ProductFactory:
    """Factory + Registry: ánh xạ định dạng → lớp sản phẩm.

    Thêm loại sách mới chỉ cần viết lớp con và gắn ``@ProductFactory.register(...)``,
    không phải sửa code tạo đối tượng ở nơi khác (nguyên lý Open/Closed).
    """

    _registry: ClassVar[dict[ProductFormat, type[Product]]] = {}

    @classmethod
    def register(cls, fmt: ProductFormat) -> Callable[[type[Product]], type[Product]]:
        def decorator(product_cls: type[Product]) -> type[Product]:
            cls._registry[fmt] = product_cls
            return product_cls

        return decorator

    @classmethod
    def create(cls, data: Mapping[str, Any]) -> Product:
        return cls.class_for(data).from_dict(data)

    @classmethod
    def class_for(cls, data: Mapping[str, Any]) -> type[Product]:
        """Lớp sản phẩm ứng với trường 'format' trong dữ liệu."""
        raw_format = optional_text(data.get("format")).upper()
        try:
            fmt = ProductFormat(raw_format)
        except ValueError:
            raise ValidationError(f"Định dạng sản phẩm không hỗ trợ: '{raw_format}'") from None
        product_cls = cls._registry.get(fmt)
        if product_cls is None:
            raise ValidationError(f"Không thể tạo sản phẩm loại '{fmt.label}' trong kho")
        return product_cls

    @classmethod
    def supported_formats(cls) -> list[ProductFormat]:
        return list(cls._registry)


@ProductFactory.register(ProductFormat.PHYSICAL)
class PhysicalBook(Book):
    """Sách in: có tồn kho thực tế, vị trí kệ và phí ship theo cân nặng."""

    EDITABLE_FIELDS = Book.EDITABLE_FIELDS + ("stock", "weight_grams", "shelf_location", "cover_type")
    BASE_SHIPPING_FEE = 20_000.0
    FREE_WEIGHT_GRAMS = 500.0
    STEP_GRAMS = 500.0
    FEE_PER_STEP = 5_000.0

    def __init__(
        self,
        *,
        stock: int | str = 0,
        weight_grams: float | str = 350,
        shelf_location: str = "",
        cover_type: str = "Bìa mềm",
        **book_kwargs: Any,
    ) -> None:
        super().__init__(**book_kwargs)
        self.stock = stock
        self.weight_grams = weight_grams
        self.shelf_location = shelf_location
        self.cover_type = cover_type

    @property
    def format(self) -> ProductFormat:
        return ProductFormat.PHYSICAL

    # ----------------------------------------------- tồn kho (ghi đè đa hình)
    @property
    def tracks_stock(self) -> bool:
        return True

    @property
    def stock(self) -> int:
        return self._stock

    @stock.setter
    def stock(self, value: int | str) -> None:
        self._stock = to_int(value, "Tồn kho")

    def stock_label(self) -> str:
        return str(self._stock)

    def can_supply(self, quantity: int) -> bool:
        return 0 < quantity <= self._stock

    def take_from_stock(self, quantity: int) -> None:
        super().take_from_stock(quantity)
        if quantity > self._stock:
            raise OutOfStockError(f"'{self.title}' chỉ còn {self._stock} cuốn (cần {quantity})")
        self._stock -= quantity

    def return_to_stock(self, quantity: int) -> None:
        self._stock += to_int(quantity, "Số lượng hoàn kho", minimum=1)

    def restock(self, quantity: int | str) -> None:
        self._stock += to_int(quantity, "Số lượng nhập", minimum=1)

    def is_low_stock(self, threshold: int) -> bool:
        return self._stock <= threshold

    # ------------------------------------------------------- thuộc tính riêng
    @property
    def weight_grams(self) -> float:
        return self._weight_grams

    @weight_grams.setter
    def weight_grams(self, value: float | str) -> None:
        self._weight_grams = to_float(value, "Trọng lượng", minimum=1)

    @property
    def shelf_location(self) -> str:
        return self._shelf_location

    @shelf_location.setter
    def shelf_location(self, value: str) -> None:
        self._shelf_location = optional_text(value) or "Kệ A-01"

    @property
    def cover_type(self) -> str:
        return self._cover_type

    @cover_type.setter
    def cover_type(self, value: str) -> None:
        self._cover_type = optional_text(value) or "Bìa mềm"

    def shipping_fee(self) -> float:
        """20.000đ cho 500g đầu, cộng 5.000đ cho mỗi 500g (hoặc phần lẻ) tiếp theo."""
        extra_grams = max(0.0, self._weight_grams - self.FREE_WEIGHT_GRAMS)
        steps = math.ceil(extra_grams / self.STEP_GRAMS)
        return self.BASE_SHIPPING_FEE + steps * self.FEE_PER_STEP

    def extra_info(self) -> dict[str, str]:
        return {
            "Trọng lượng": f"{self._weight_grams:g} g",
            "Vị trí kệ": self._shelf_location,
            "Loại bìa": self._cover_type,
        }

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            stock=self._stock,
            weight_grams=self._weight_grams,
            shelf_location=self._shelf_location,
            cover_type=self._cover_type,
        )
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PhysicalBook":
        return cls(
            **cls._book_kwargs(data),
            stock=data.get("stock", 0),
            weight_grams=data.get("weight_grams", 350),
            shelf_location=data.get("shelf_location", ""),
            cover_type=data.get("cover_type", "Bìa mềm"),
        )


@ProductFactory.register(ProductFormat.EBOOK)
class EBook(Book):
    """Sách điện tử trong Kho Drive: không bán lẻ, chỉ hội viên còn hạn mới thấy link.

    Link Drive chỉ được cấp cho khách qua ``EBookVault.open_ebook()`` (kiểm tra quyền hội viên).
    """

    EDITABLE_FIELDS = Book.EDITABLE_FIELDS + ("file_format", "file_size_mb", "drive_link")

    def __init__(
        self,
        *,
        file_format: str = "PDF",
        file_size_mb: float | str = 1.0,
        drive_link: str = "",
        **book_kwargs: Any,
    ) -> None:
        super().__init__(**book_kwargs)
        self.file_format = file_format
        self.file_size_mb = file_size_mb
        self.drive_link = drive_link

    @property
    def format(self) -> ProductFormat:
        return ProductFormat.EBOOK

    @property
    def purchasable(self) -> bool:
        return False

    def stock_label(self) -> str:
        return "Kho hội viên"

    @property
    def file_format(self) -> str:
        return self._file_format

    @file_format.setter
    def file_format(self, value: str) -> None:
        self._file_format = optional_text(value).upper() or "PDF"

    @property
    def file_size_mb(self) -> float:
        return self._file_size_mb

    @file_size_mb.setter
    def file_size_mb(self, value: float | str) -> None:
        self._file_size_mb = to_float(value, "Dung lượng file")

    @property
    def drive_link(self) -> str:
        return self._drive_link

    @drive_link.setter
    def drive_link(self, value: str) -> None:
        link = optional_text(value)
        if link and not link.startswith(("http://", "https://")):
            raise ValidationError("Link Google Drive phải bắt đầu bằng http:// hoặc https://")
        self._drive_link = link

    @property
    def has_drive_link(self) -> bool:
        return bool(self._drive_link)

    def shipping_fee(self) -> float:
        return 0.0

    def extra_info(self) -> dict[str, str]:
        return {
            "Định dạng file": self._file_format,
            "Dung lượng": f"{self._file_size_mb:g} MB",
            "Link Drive": "Đã cấu hình" if self.has_drive_link else "Chưa có",
        }

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(file_format=self._file_format, file_size_mb=self._file_size_mb, drive_link=self._drive_link)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EBook":
        return cls(
            **cls._book_kwargs(data),
            file_format=data.get("file_format", "PDF"),
            file_size_mb=data.get("file_size_mb", 1.0),
            drive_link=data.get("drive_link") or data.get("download_link") or "",
        )


class MembershipPlan(Product):
    """Gói hội viên Kho E-Book.

    Kế thừa ``Product`` để đi chung luồng hóa đơn với sách (đa hình), nhưng không đăng ký
    vào ``ProductFactory`` vì đây không phải hàng hóa nằm trong kho.
    """

    ID_PREFIX = "MEM"
    CATEGORY = "Hội viên E-Book"

    def __init__(
        self,
        *,
        product_id: str = "MEM-EBOOK",
        title: str = "Gói Hội Viên Kho E-Book",
        price: float = 100_000,
        duration_days: int = 365,
    ) -> None:
        super().__init__(product_id=product_id, title=title, price=price, category=self.CATEGORY)
        self._duration_days = to_int(duration_days, "Thời hạn gói", minimum=1)

    @property
    def format(self) -> ProductFormat:
        return ProductFormat.MEMBERSHIP

    @property
    def duration_days(self) -> int:
        return self._duration_days

    def shipping_fee(self) -> float:
        return 0.0

    def extra_info(self) -> dict[str, str]:
        return {"Thời hạn": f"{self._duration_days} ngày"}

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["duration_days"] = self._duration_days
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MembershipPlan":
        return cls(
            product_id=data.get("id", "MEM-EBOOK"),
            title=data.get("title", "Gói Hội Viên Kho E-Book"),
            price=data.get("price", 100_000),
            duration_days=data.get("duration_days", 365),
        )
