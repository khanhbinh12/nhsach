"""Dữ liệu mẫu ban đầu của nhà sách.

Tài khoản demo:
    Quản trị viên: admin / admin123
    Khách hàng:    nam.nt@example.com / 123456  (đang là hội viên E-Book)
                   quan.lh@example.com / 123456
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from ..models import Cart, CustomerAccount, CustomerFactory, PasswordHasher

if TYPE_CHECKING:
    from .bookstore import Bookstore

DEMO_PASSWORD = "123456"
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin123"


class SampleDataSeeder:
    PHYSICAL_BOOKS = (
        {"id": "BK-OOP-01", "title": "Lập Trình Hướng Đối Tượng Python Nâng Cao", "author": "TS. Nguyễn Văn Toàn",
         "category": "Công nghệ & Lập trình", "price": 185000, "stock": 18, "isbn": "978-604-01-2891-2",
         "publisher": "NXB Thông Tin & Truyền Thông", "publish_year": 2024, "weight_grams": 620,
         "shelf_location": "Kệ IT-03", "cover_type": "Bìa mềm",
         "description": "Giáo trình về 4 trụ cột OOP, Design Patterns và kiến trúc phần mềm trong Python."},
        {"id": "BK-LIT-02", "title": "Dế Mèn Phiêu Lưu Ký (Ấn Bản Đặc Biệt)", "author": "Tô Hoài",
         "category": "Văn học Việt Nam", "price": 120000, "stock": 35, "isbn": "978-604-02-1145-0",
         "publisher": "NXB Kim Đồng", "publish_year": 2023, "weight_grams": 450, "shelf_location": "Kệ VH-01",
         "cover_type": "Bìa cứng", "description": "Kiệt tác văn học thiếu nhi Việt Nam với minh họa màu."},
        {"id": "BK-BIZ-03", "title": "Tâm Lý Học Về Tiền", "author": "Morgan Housel",
         "category": "Kinh tế & Tài chính", "price": 149000, "stock": 4, "isbn": "978-604-03-9081-4",
         "publisher": "NXB Trẻ", "publish_year": 2023, "weight_grams": 480, "shelf_location": "Kệ KT-02",
         "description": "Bài học về sự giàu có, lòng tham và hạnh phúc qua lăng kính tâm lý học."},
        {"id": "BK-LIT-04", "title": "Số Đỏ (Tái Bản Minh Họa)", "author": "Vũ Trọng Phụng",
         "category": "Văn học Việt Nam", "price": 115000, "stock": 3, "isbn": "978-604-04-1229-7",
         "publisher": "NXB Văn Học", "publish_year": 2022, "weight_grams": 390, "shelf_location": "Kệ VH-02",
         "description": "Tác phẩm trào phúng sắc sảo của văn học hiện thực phê phán."},
        {"id": "BK-SCI-05", "title": "Vũ Trụ Trong Vỏ Hạt Dẻ", "author": "Stephen Hawking",
         "category": "Khoa học", "price": 195000, "stock": 12, "isbn": "978-604-05-3310-9",
         "publisher": "NXB Trẻ", "publish_year": 2022, "weight_grams": 1040, "shelf_location": "Kệ KH-01",
         "cover_type": "Bìa cứng", "description": "Khám phá biên giới của vật lý lý thuyết, lỗ đen và thuyết lượng tử."},
        {"id": "BK-SKL-06", "title": "Đắc Nhân Tâm", "author": "Dale Carnegie",
         "category": "Kỹ năng sống", "price": 128000, "stock": 22, "isbn": "978-604-06-1120-3",
         "publisher": "First News", "publish_year": 2024, "weight_grams": 410, "shelf_location": "Kệ KN-01",
         "description": "Nghệ thuật thu phục lòng người – cuốn sách kỹ năng bán chạy mọi thời đại."},
        {"id": "BK-LIT-07", "title": "Truyện Kiều (Bản Chú Giải)", "author": "Nguyễn Du",
         "category": "Văn học Việt Nam", "price": 135000, "stock": 9, "isbn": "978-604-07-5521-8",
         "publisher": "NXB Giáo Dục", "publish_year": 2023, "weight_grams": 560, "shelf_location": "Kệ VH-03",
         "cover_type": "Bìa cứng", "description": "Kiệt tác thơ lục bát kèm chú giải từ ngữ và điển cố."},
        {"id": "BK-BIZ-08", "title": "Khởi Nghiệp Tinh Gọn", "author": "Eric Ries",
         "category": "Kinh tế & Tài chính", "price": 142000, "stock": 15, "isbn": "978-604-08-2210-6",
         "publisher": "NXB Lao Động", "publish_year": 2023, "weight_grams": 470, "shelf_location": "Kệ KT-01",
         "description": "Phương pháp xây dựng sản phẩm bằng vòng lặp Xây dựng – Đo lường – Học hỏi."},
    )

    EBOOKS = (
        {"id": "EB-001", "title": "Clean Code – Mã Sạch", "author": "Robert C. Martin",
         "category": "Công nghệ & Lập trình", "file_size_mb": 12.8, "file_format": "PDF",
         "drive_link": "https://drive.google.com/file/d/demo-clean-code/view",
         "description": "Quy chuẩn viết code sạch, dễ bảo trì và mở rộng."},
        {"id": "EB-002", "title": "Deep Work – Làm Ra Làm, Chơi Ra Chơi", "author": "Cal Newport",
         "category": "Kỹ năng sống", "file_size_mb": 8.4, "file_format": "EPUB",
         "drive_link": "https://drive.google.com/file/d/demo-deep-work/view",
         "description": "Chiến lược rèn luyện sự tập trung cao độ."},
        {"id": "EB-003", "title": "Atomic Habits – Thay Đổi Tí Hon", "author": "James Clear",
         "category": "Kỹ năng sống", "file_size_mb": 10.2, "file_format": "PDF",
         "drive_link": "https://drive.google.com/file/d/demo-atomic-habits/view",
         "description": "Phương pháp xây dựng thói quen tốt bền vững."},
        {"id": "EB-004", "title": "Lão Hạc và Các Truyện Ngắn", "author": "Nam Cao",
         "category": "Văn học Việt Nam", "file_size_mb": 3.1, "file_format": "EPUB",
         "drive_link": "https://drive.google.com/file/d/demo-lao-hac/view",
         "description": "Tuyển tập truyện ngắn hiện thực xuất sắc."},
        {"id": "EB-005", "title": "Lược Sử Thời Gian", "author": "Stephen Hawking",
         "category": "Khoa học", "file_size_mb": 15.6, "file_format": "PDF",
         "drive_link": "https://drive.google.com/file/d/demo-luoc-su-thoi-gian/view",
         "description": "Từ Vụ Nổ Lớn tới lỗ đen, giải thích dễ hiểu cho mọi người."},
        {"id": "EB-006", "title": "Python Cho Người Mới Bắt Đầu", "author": "Nhóm Tác Giả Trí Tri",
         "category": "Công nghệ & Lập trình", "file_size_mb": 6.7, "file_format": "PDF",
         "drive_link": "https://drive.google.com/file/d/demo-python-co-ban/view",
         "description": "Nhập môn lập trình Python qua 30 bài tập thực hành."},
    )

    CUSTOMERS = (
        {"id": "KH-VIP01", "type": "VIP", "name": "Nguyễn Thành Nam", "phone": "0912345678",
         "email": "nam.nt@example.com", "loyalty_points": 240, "total_spent": 4_200_000, "base_tier": "SILVER"},
        {"id": "KH-VIP02", "type": "VIP", "name": "Trần Mai Phương", "phone": "0987654321",
         "email": "phuong.tm@example.com", "loyalty_points": 520, "total_spent": 9_500_000, "base_tier": "GOLD"},
        {"id": "KH-REG03", "type": "STANDARD", "name": "Lê Hoàng Quân", "phone": "0905123987",
         "email": "quan.lh@example.com", "loyalty_points": 45, "total_spent": 450_000},
        {"id": "KH-REG04", "type": "STANDARD", "name": "Vũ Minh Anh", "phone": "0934112233",
         "email": "minhanh.vu@example.com", "loyalty_points": 80, "total_spent": 800_000},
    )

    VOUCHERS = (
        {"kind": "PERCENT", "code": "TRITRI10", "value": 10, "min_subtotal": 200_000, "usage_limit": 100},
        {"kind": "FIXED", "code": "GIAM30K", "value": 30_000, "min_subtotal": 150_000, "usage_limit": 50},
    )

    def __init__(self, store: "Bookstore") -> None:
        self._store = store

    def populate(self) -> None:
        store = self._store
        for data in self.PHYSICAL_BOOKS:
            store.inventory.create({**data, "format": "PHYSICAL"})
        for data in self.EBOOKS:
            store.inventory.create({**data, "format": "EBOOK"})

        demo_hash = PasswordHasher.hash(DEMO_PASSWORD)  # băm một lần, dùng chung cho dữ liệu demo
        for data in self.CUSTOMERS:
            customer = store.customers.add(CustomerFactory.from_dict(data))
            store.accounts.add(CustomerAccount(login=customer.email, password_hash=demo_hash, customer_id=customer.id))
        store.accounts.create_admin(login=ADMIN_LOGIN, password=ADMIN_PASSWORD, display_name="Chủ nhà sách")

        orders = store.orders
        address = "12 Lê Lợi, Q.1, TP.HCM"
        first = self._order("KH-VIP01", [("BK-OOP-01", 1), ("BK-SKL-06", 1)], address)
        second = self._order("KH-REG03", [("BK-LIT-02", 2)], "45 Trần Phú, Hải Châu, Đà Nẵng")
        third = self._order("KH-VIP02", [("BK-BIZ-03", 1), ("BK-SCI-05", 1), ("BK-LIT-07", 1), ("BK-BIZ-08", 1)],
                            "8 Nguyễn Huệ, TP. Huế")
        shipping = self._order("KH-REG03", [("BK-SKL-06", 1)], "45 Trần Phú, Hải Châu, Đà Nẵng")
        self._order("KH-REG04", [("BK-LIT-04", 1)], "102 Cầu Giấy, Hà Nội")  # để ở trạng thái chờ xử lý
        for order in (first, second, third, shipping):
            orders.ship(order.id)
        for order in (first, second, third):
            orders.complete(order.id)  # đơn `shipping` để ở trạng thái "Đang giao"

        today = store.now().date()
        for voucher in self.VOUCHERS:
            store.vouchers.create({**voucher, "valid_until": (today + timedelta(days=90)).isoformat()})

        nam = store.customers.get("KH-VIP01")
        orders.complete(store.membership.request(nam).id)       # hội viên đã kích hoạt
        store.membership.request(store.customers.get("KH-REG03"))  # chờ admin xác nhận

        for days_ago, views in enumerate((14, 9, 21, 12, 17, 8, 11)):
            for _ in range(views):
                store.ads.ledger.record(store.now() - timedelta(days=days_ago))

    def _order(self, customer_id: str, items: list[tuple[str, int]], address: str):
        cart = Cart()
        for product_id, quantity in items:
            cart.add(self._store.inventory.get(product_id), quantity)
        return self._store.orders.place_order(
            cart,
            customer=self._store.customers.get(customer_id),
            payment_method="Thanh toán khi nhận hàng (COD)",
            shipping_address=address,
        )
