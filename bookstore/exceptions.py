"""Cây ngoại lệ nghiệp vụ.

Mọi lỗi nghiệp vụ đều kế thừa ``BookstoreError`` để tầng web chỉ cần bắt một loại
ngoại lệ duy nhất và hiển thị thông báo thân thiện cho người dùng.
"""


class BookstoreError(Exception):
    """Lỗi nghiệp vụ gốc của hệ thống nhà sách."""


class ValidationError(BookstoreError):
    """Dữ liệu nhập vào không hợp lệ."""


class NotFoundError(BookstoreError):
    """Không tìm thấy đối tượng được yêu cầu."""


class OutOfStockError(BookstoreError):
    """Tồn kho không đủ để đáp ứng yêu cầu."""


class UnsupportedOperationError(BookstoreError):
    """Thao tác không áp dụng cho loại đối tượng này."""


class AccessDeniedError(BookstoreError):
    """Không có quyền truy cập tài nguyên (ví dụ: link Drive khi chưa là hội viên)."""


class AuthenticationError(BookstoreError):
    """Sai thông tin đăng nhập."""


class DataCorruptedError(BookstoreError):
    """File dữ liệu bị hỏng hoặc sai định dạng."""
