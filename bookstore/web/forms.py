"""Form thêm / sửa sách cho trang quản trị.

Cây kế thừa song song với model:  ProductForm (trừu tượng) → PhysicalBookForm, EBookForm.
Lớp con tự đăng ký theo ``FORMAT`` qua ``__init_subclass__``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from ..models import Product, ProductFormat


@dataclass(frozen=True)
class FormField:
    name: str
    label: str
    kind: str = "text"  # text | number | url | textarea
    required: bool = False
    help: str = ""


class ProductForm(ABC):
    FORMAT: ClassVar[ProductFormat]
    _registry: ClassVar[dict[ProductFormat, type["ProductForm"]]] = {}

    ID_FIELD = FormField("id", "Mã sách", help="Bỏ trống để hệ thống tự sinh mã")
    COMMON_FIELDS: ClassVar[tuple[FormField, ...]] = (
        FormField("title", "Tên sách", required=True),
        FormField("author", "Tác giả", required=True),
        FormField("category", "Thể loại"),
        FormField("isbn", "ISBN"),
        FormField("publisher", "Nhà xuất bản"),
        FormField("publish_year", "Năm xuất bản", "number"),
        FormField("description", "Mô tả", "textarea"),
    )
    SPECIFIC_FIELDS: ClassVar[tuple[FormField, ...]] = ()
    DEFAULTS: ClassVar[dict[str, Any]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "FORMAT" in cls.__dict__:
            ProductForm._registry[cls.FORMAT] = cls

    def __init__(self, product: Product | None = None, data: Mapping[str, Any] | None = None) -> None:
        self.product = product
        self._values: dict[str, Any] = dict(product.to_dict()) if product else {"publish_year": 2025, **self.DEFAULTS}
        if data:
            self._values.update({key: data.get(key, "") for key in data})

    @property
    @abstractmethod
    def heading(self) -> str:
        """Tiêu đề hiển thị của form."""

    @property
    def is_edit(self) -> bool:
        return self.product is not None

    @property
    def common_fields(self) -> tuple[FormField, ...]:
        return self.COMMON_FIELDS if self.is_edit else (self.ID_FIELD, *self.COMMON_FIELDS)

    @property
    def fields(self) -> tuple[FormField, ...]:
        return self.common_fields + self.SPECIFIC_FIELDS

    def value(self, name: str) -> str:
        value = self._values.get(name, "")
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def submitted_data(self, form: Mapping[str, Any]) -> dict[str, Any]:
        data = {field.name: form.get(field.name, "") for field in self.fields}
        data["format"] = self.FORMAT.value
        if self.is_edit:
            data.pop("id", None)
        return data

    @classmethod
    def for_format(cls, fmt: ProductFormat) -> type["ProductForm"]:
        return cls._registry[fmt]

    @classmethod
    def for_product(cls, product: Product) -> "ProductForm":
        return cls._registry[product.format](product)


class PhysicalBookForm(ProductForm):
    FORMAT = ProductFormat.PHYSICAL
    SPECIFIC_FIELDS = (
        FormField("price", "Giá bán (đ)", "number", required=True),
        FormField("stock", "Tồn kho", "number", required=True),
        FormField("weight_grams", "Trọng lượng (gram)", "number", help="Dùng để tính phí ship"),
        FormField("shelf_location", "Vị trí kệ"),
        FormField("cover_type", "Loại bìa"),
    )
    DEFAULTS = {"price": 120000, "stock": 10, "weight_grams": 400, "shelf_location": "Kệ A-01", "cover_type": "Bìa mềm"}

    @property
    def heading(self) -> str:
        return "Sách giấy"


class EBookForm(ProductForm):
    FORMAT = ProductFormat.EBOOK
    SPECIFIC_FIELDS = (
        FormField("file_format", "Định dạng file", help="PDF hoặc EPUB"),
        FormField("file_size_mb", "Dung lượng (MB)", "number"),
        FormField("drive_link", "Link Google Drive", "url", help="Chỉ hội viên còn hạn mới nhìn thấy link này"),
    )
    DEFAULTS = {"file_format": "PDF", "file_size_mb": 5}

    @property
    def heading(self) -> str:
        return "E-Book (Kho hội viên)"
