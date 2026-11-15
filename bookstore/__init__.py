"""Hệ thống Quản Lý Nhà Sách Trí Tri – ứng dụng desktop viết bằng Python theo hướng đối tượng.

Kiến trúc phân lớp:
    models/    Lớp nghiệp vụ (thực thể, chính sách giảm giá, hóa đơn)
    services/  Lớp dịch vụ điều phối nghiệp vụ + Facade ``Bookstore``
    storage.py Lưu trữ dữ liệu (Repository trừu tượng + file JSON)
    ui/        Giao diện Tkinter
"""

__version__ = "2.0.0"
