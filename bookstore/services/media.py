"""Lưu ảnh bìa sách tải lên: kiểm tra ảnh thật, tạo ảnh lớn + ảnh thu nhỏ định dạng WEBP.

Trước đây ảnh gốc (tới 2 MB) được dùng nguyên cho cả ô bìa nhỏ 54 px trong giỏ hàng.
Nay mỗi ảnh được lưu thành 2 bản: ``<mã>.webp`` (tối đa 600×800, trang chi tiết) và
``<mã>-thumb.webp`` (tối đa 240×320, danh sách / giỏ hàng).
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from ..exceptions import ValidationError
from ..models import DEFAULT_IDS


class CoverImageStore:
    """Kho ảnh bìa trên đĩa."""

    MAX_BYTES = 2 * 1024 * 1024
    MAX_PIXELS = 25_000_000  # chặn ảnh "bom giải nén" (file nhỏ nhưng hàng trăm triệu điểm ảnh)
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
    FULL_SIZE = (600, 800)
    THUMB_SIZE = (240, 320)
    OUTPUT_EXTENSION = ".webp"
    THUMB_SUFFIX = "-thumb"
    QUALITY = 82

    def __init__(self, folder: str | Path) -> None:
        self._folder = Path(folder)

    @property
    def folder(self) -> Path:
        return self._folder

    # ------------------------------------------------------------- lưu ảnh
    def save(self, product_id: str, original_name: str, data: bytes) -> str:
        """Kiểm tra, thu nhỏ và lưu ảnh; trả về tên file ảnh lớn."""
        image = self._decode(original_name, data)
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", product_id)
        self._folder.mkdir(parents=True, exist_ok=True)
        stem = DEFAULT_IDS.new_id(safe_id, lambda candidate: self._path(candidate + self.OUTPUT_EXTENSION).exists())
        name = stem + self.OUTPUT_EXTENSION
        self._write(image, name, self.FULL_SIZE)
        self._write(image, self.thumb_name(name), self.THUMB_SIZE)
        return name

    def _decode(self, original_name: str, data: bytes) -> Image.Image:
        extension = Path(original_name or "").suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError("Chỉ nhận ảnh bìa định dạng JPG, PNG hoặc WEBP")
        if not data:
            raise ValidationError("File ảnh trống")
        if len(data) > self.MAX_BYTES:
            raise ValidationError(f"Ảnh bìa tối đa {self.MAX_BYTES // (1024 * 1024)} MB")
        try:
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in self.ALLOWED_FORMATS:
                    raise ValidationError("File tải lên không phải ảnh JPG, PNG hoặc WEBP hợp lệ")
                if probe.width * probe.height > self.MAX_PIXELS:
                    raise ValidationError("Ảnh có kích thước quá lớn")
                probe.verify()  # kiểm tra cấu trúc file; sau verify() phải mở lại mới dùng được
            image = Image.open(io.BytesIO(data))
            image.load()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
            raise ValidationError("File tải lên không phải ảnh hợp lệ") from None
        image = ImageOps.exif_transpose(image)  # ảnh chụp điện thoại: xoay đúng chiều
        return image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")

    def _write(self, image: Image.Image, name: str, max_size: tuple[int, int]) -> None:
        resized = image.copy()
        resized.thumbnail(max_size, Image.Resampling.LANCZOS)  # giữ tỉ lệ, chỉ thu nhỏ
        resized.save(self._path(name), "WEBP", quality=self.QUALITY, method=4)

    # ------------------------------------------------------------- tra cứu & xóa
    @classmethod
    def thumb_name(cls, name: str) -> str:
        path = Path(name)
        return f"{path.stem}{cls.THUMB_SUFFIX}{path.suffix}"

    def thumb_or_original(self, name: str) -> str:
        """Ảnh thu nhỏ nếu có (ảnh tải lên từ bản cũ không có thumbnail thì dùng ảnh gốc)."""
        thumb = self.thumb_name(name)
        return thumb if self._path(thumb).is_file() else name

    def delete(self, name: str) -> None:
        if not name:
            return
        for candidate in (name, self.thumb_name(name)):
            path = self._path(candidate).resolve()
            if path.parent == self._folder.resolve() and path.is_file():
                path.unlink()

    def _path(self, name: str) -> Path:
        return self._folder / name
