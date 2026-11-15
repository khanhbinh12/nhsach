"""
Hệ Thống Quản Lý Nhà Sách Hướng Đối Tượng (Python OOP Bookstore System)
Áp dụng 4 trụ cột OOP:
1. Trừu tượng (Abstraction): Lớp trừu tượng Item, DiscountPolicy với abc.ABC
2. Đóng gói (Encapsulation): Thuộc tính private/protected (_price, _stock, _points), @property, setter kiểm tra tính hợp lệ
3. Kế thừa (Inheritance):
   - Item -> Book -> PhysicalBook, EBook, AudioBook
   - Person -> Customer -> VIPCustomer, Staff
   - DiscountPolicy -> NoDiscount, VIPDiscount, SeasonalDiscount, BulkDiscount
4. Đa hình (Polymorphism):
   - calculate_shipping_fee() thực thi khác nhau giữa PhysicalBook (tính theo trọng lượng) và EBook/AudioBook (miễn phí)
   - calculate_discount() áp dụng chính sách giảm giá linh hoạt tại thời điểm thanh toán
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import json
import os
import uuid


# ==========================================
# 1. ENUMS & VALUE OBJECTS
# ==========================================

class BookFormat(str, Enum):
    PHYSICAL = "PHYSICAL"
    EBOOK = "EBOOK"
    AUDIOBOOK = "AUDIOBOOK"


class OrderStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


class VIPTier(str, Enum):
    STANDARD = "STANDARD"
    BRONZE = "BRONZE"      # 5% giảm
    SILVER = "SILVER"      # 10% giảm
    GOLD = "GOLD"          # 15% giảm
    PLATINUM = "PLATINUM"  # 20% giảm


# ==========================================
# 2. ABSTRACTION & INHERITANCE: ITEM HIERARCHY
# ==========================================

class Item(ABC):
    """Lớp trừu tượng đại diện cho một sản phẩm trong nhà sách (Tính trừu tượng)"""
    
    def __init__(self, item_id: str, title: str, author: str, category: str, price: float, stock: int = 0):
        # Tính đóng gói (Encapsulation): Bảo vệ các thuộc tính nhạy cảm
        self._id = item_id or str(uuid.uuid4())[:8]
        self._title = title.strip()
        self._author = author.strip()
        self._category = category.strip()
        self._price = max(0.0, float(price))
        self._stock = max(0, int(stock))
        self._created_at = datetime.now().isoformat()

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        if not value or not value.strip():
            raise ValueError("Tên sách không được để trống")
        self._title = value.strip()

    @property
    def author(self) -> str:
        return self._author

    @author.setter
    def author(self, value: str):
        if not value or not value.strip():
            raise ValueError("Tác giả không được để trống")
        self._author = value.strip()

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str):
        self._category = value.strip()

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float):
        if value < 0:
            raise ValueError("Giá sản phẩm không thể âm")
        self._price = float(value)

    @property
    def stock(self) -> int:
        return self._stock

    @stock.setter
    def stock(self, value: int):
        if value < 0:
            raise ValueError("Số lượng tồn kho không thể âm")
        self._stock = int(value)

    def reduce_stock(self, quantity: int) -> bool:
        """Đóng gói logic trừ tồn kho có xác thực"""
        if quantity <= 0:
            raise ValueError("Số lượng giảm phải lớn hơn 0")
        if self._stock < quantity:
            return False
        self._stock -= quantity
        return True

    def restock(self, quantity: int):
        """Đóng gói logic nhập thêm hàng"""
        if quantity <= 0:
            raise ValueError("Số lượng nhập phải lớn hơn 0")
        self._stock += quantity

    @abstractmethod
    def get_format(self) -> BookFormat:
        """Phương thức trừu tượng xác định định dạng"""
        pass

    @abstractmethod
    def calculate_shipping_fee(self) -> float:
        """Phương thức trừu tượng tính phí vận chuyển (Thể hiện tính đa hình)"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi đối tượng sang dictionary để serialize JSON"""
        pass


class Book(Item):
    """Lớp trung gian kế thừa từ Item bổ sung thông tin xuất bản"""
    
    def __init__(self, item_id: str, title: str, author: str, category: str, 
                 price: float, stock: int, isbn: str, publisher: str, publish_year: int, description: str = ""):
        super().__init__(item_id, title, author, category, price, stock)
        self._isbn = isbn
        self._publisher = publisher
        self._publish_year = int(publish_year)
        self._description = description

    @property
    def isbn(self) -> str:
        return self._isbn

    @property
    def publisher(self) -> str:
        return self._publisher

    @property
    def publish_year(self) -> int:
        return self._publish_year

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value


class PhysicalBook(Book):
    """
    Sách in truyền thống (Kế thừa từ Book).
    Bổ sung trọng lượng (gam), vị trí kệ sách và loại bìa.
    """
    def __init__(self, item_id: str, title: str, author: str, category: str, price: float, 
                 stock: int, isbn: str, publisher: str, publish_year: int, 
                 weight_grams: float, shelf_location: str, cover_type: str = "Bìa mềm", 
                 description: str = ""):
        super().__init__(item_id, title, author, category, price, stock, isbn, publisher, publish_year, description)
        self._weight_grams = max(50.0, float(weight_grams))
        self._shelf_location = shelf_location.strip() or "Kệ A-01"
        self._cover_type = cover_type

    @property
    def weight_grams(self) -> float:
        return self._weight_grams

    @property
    def shelf_location(self) -> str:
        return self._shelf_location

    @shelf_location.setter
    def shelf_location(self, value: str):
        self._shelf_location = value.strip()

    @property
    def cover_type(self) -> str:
        return self._cover_type

    def get_format(self) -> BookFormat:
        return BookFormat.PHYSICAL

    def calculate_shipping_fee(self) -> float:
        """
        ĐA HÌNH (Polymorphism):
        Sách in tính phí ship cơ bản 20,000 VND + 5,000 VND cho mỗi 500g vượt quá 500g đầu.
        """
        base_fee = 20000.0
        if self._weight_grams > 500:
            extra_weight = self._weight_grams - 500
            extra_fee = (extra_weight // 500 + 1) * 5000.0
            return base_fee + extra_fee
        return base_fee

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "title": self._title,
            "author": self._author,
            "category": self._category,
            "price": self._price,
            "stock": self._stock,
            "isbn": self._isbn,
            "publisher": self._publisher,
            "publish_year": self._publish_year,
            "description": self._description,
            "format": self.get_format().value,
            "weight_grams": self._weight_grams,
            "shelf_location": self._shelf_location,
            "cover_type": self._cover_type,
            "shipping_fee": self.calculate_shipping_fee()
        }


class EBook(Book):
    """
    Sách điện tử E-Book (Kế thừa từ Book).
    Không tốn kho thực tế (stock tượng trưng), dung lượng file, link tải.
    """
    def __init__(self, item_id: str, title: str, author: str, category: str, price: float, 
                 isbn: str, publisher: str, publish_year: int, 
                 file_size_mb: float, file_format: str = "PDF", download_link: str = "", 
                 description: str = ""):
        # EBook luôn có sẵn, stock mặc định 9999
        super().__init__(item_id, title, author, category, price, 9999, isbn, publisher, publish_year, description)
        self._file_size_mb = float(file_size_mb)
        self._file_format = file_format.upper()
        self._download_link = download_link or f"https://bookstore.vn/download/{self._id}.{self._file_format.lower()}"

    @property
    def file_size_mb(self) -> float:
        return self._file_size_mb

    @property
    def file_format(self) -> str:
        return self._file_format

    @property
    def download_link(self) -> str:
        return self._download_link

    def get_format(self) -> BookFormat:
        return BookFormat.EBOOK

    def calculate_shipping_fee(self) -> float:
        """ĐA HÌNH: E-Book gửi qua email/tải trực tuyến nên phí vận chuyển luôn là 0 VND"""
        return 0.0

    def reduce_stock(self, quantity: int) -> bool:
        # E-Book không bao giờ hết hàng
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "title": self._title,
            "author": self._author,
            "category": self._category,
            "price": self._price,
            "stock": 9999,
            "isbn": self._isbn,
            "publisher": self._publisher,
            "publish_year": self._publish_year,
            "description": self._description,
            "format": self.get_format().value,
            "file_size_mb": self._file_size_mb,
            "file_format": self._file_format,
            "download_link": self._download_link,
            "shipping_fee": 0.0
        }


class AudioBook(Book):
    """
    Sách nói Audio Book (Kế thừa từ Book).
    Bổ sung thời lượng (phút), người đọc (giọng đọc).
    """
    def __init__(self, item_id: str, title: str, author: str, category: str, price: float, 
                 isbn: str, publisher: str, publish_year: int, 
                 duration_minutes: int, narrator: str, sample_audio_url: str = "", 
                 description: str = ""):
        super().__init__(item_id, title, author, category, price, 9999, isbn, publisher, publish_year, description)
        self._duration_minutes = int(duration_minutes)
        self._narrator = narrator.strip()
        self._sample_audio_url = sample_audio_url

    @property
    def duration_minutes(self) -> int:
        return self._duration_minutes

    @property
    def narrator(self) -> str:
        return self._narrator

    @property
    def sample_audio_url(self) -> str:
        return self._sample_audio_url

    def get_format(self) -> BookFormat:
        return BookFormat.AUDIOBOOK

    def calculate_shipping_fee(self) -> float:
        """ĐA HÌNH: Sách nói nghe trực tuyến không mất phí ship"""
        return 0.0

    def reduce_stock(self, quantity: int) -> bool:
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "title": self._title,
            "author": self._author,
            "category": self._category,
            "price": self._price,
            "stock": 9999,
            "isbn": self._isbn,
            "publisher": self._publisher,
            "publish_year": self._publish_year,
            "description": self._description,
            "format": self.get_format().value,
            "duration_minutes": self._duration_minutes,
            "narrator": self._narrator,
            "sample_audio_url": self._sample_audio_url,
            "shipping_fee": 0.0
        }


# ==========================================
# 3. PERSON & CUSTOMER HIERARCHY
# ==========================================

class Person(ABC):
    """Lớp trừu tượng đại diện cho con người trong hệ thống"""
    def __init__(self, person_id: str, name: str, phone: str, email: str):
        self._id = person_id or str(uuid.uuid4())[:8]
        self._name = name.strip()
        self._phone = phone.strip()
        self._email = email.strip()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def email(self) -> str:
        return self._email


class Customer(Person):
    """Khách hàng thông thường"""
    def __init__(self, customer_id: str, name: str, phone: str, email: str, 
                 loyalty_points: int = 0, total_spent: float = 0.0):
        super().__init__(customer_id, name, phone, email)
        self._loyalty_points = max(0, loyalty_points)
        self._total_spent = max(0.0, float(total_spent))
        self._joined_date = datetime.now().strftime("%Y-%m-%d")

    @property
    def loyalty_points(self) -> int:
        return self._loyalty_points

    @property
    def total_spent(self) -> float:
        return self._total_spent

    def add_loyalty_points(self, points: int):
        if points > 0:
            self._loyalty_points += points

    def use_loyalty_points(self, points: int) -> bool:
        if 0 < points <= self._loyalty_points:
            self._loyalty_points -= points
            return True
        return False

    def record_purchase(self, amount: float):
        if amount > 0:
            self._total_spent += amount
            # 10,000 VND chi tiêu = 1 điểm tích lũy
            earned_points = int(amount // 10000)
            self.add_loyalty_points(earned_points)

    def get_tier(self) -> VIPTier:
        return VIPTier.STANDARD

    def get_discount_rate(self) -> float:
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "name": self._name,
            "phone": self._phone,
            "email": self._email,
            "loyalty_points": self._loyalty_points,
            "total_spent": self._total_spent,
            "tier": self.get_tier().value,
            "discount_rate": self.get_discount_rate(),
            "joined_date": self._joined_date,
            "is_vip": False
        }


class VIPCustomer(Customer):
    """
    Khách hàng VIP (Kế thừa từ Customer).
    Tự động xác định cấp VIP dựa trên chi tiêu hoặc được cấp hạng trực tiếp.
    """
    def __init__(self, customer_id: str, name: str, phone: str, email: str, 
                 loyalty_points: int = 0, total_spent: float = 0.0, 
                 tier: VIPTier = VIPTier.BRONZE):
        super().__init__(customer_id, name, phone, email, loyalty_points, total_spent)
        self._tier = tier

    def get_tier(self) -> VIPTier:
        # Nếu chi tiêu vượt ngưỡng, tự nâng hạng VIP
        if self._total_spent >= 15000000:
            return VIPTier.PLATINUM
        elif self._total_spent >= 8000000:
            return VIPTier.GOLD
        elif self._total_spent >= 3000000:
            return VIPTier.SILVER
        return self._tier if self._tier != VIPTier.STANDARD else VIPTier.BRONZE

    def get_discount_rate(self) -> float:
        """ĐA HÌNH: Tỷ lệ chiết khấu cố định theo hạng VIP"""
        tier = self.get_tier()
        rates = {
            VIPTier.BRONZE: 0.05,    # 5%
            VIPTier.SILVER: 0.10,    # 10%
            VIPTier.GOLD: 0.15,      # 15%
            VIPTier.PLATINUM: 0.20   # 20%
        }
        return rates.get(tier, 0.05)

    def record_purchase(self, amount: float):
        """Khách VIP nhận điểm tích lũy nhân đôi"""
        if amount > 0:
            self._total_spent += amount
            earned_points = int((amount // 10000) * 2)  # 2x điểm
            self.add_loyalty_points(earned_points)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["is_vip"] = True
        base["tier"] = self.get_tier().value
        base["discount_rate"] = self.get_discount_rate()
        return base


# ==========================================
# 4. POLYMORPHISM: STRATEGY PATTERN FOR DISCOUNTS
# ==========================================

class DiscountPolicy(ABC):
    """Lớp trừu tượng chính sách giảm giá (Strategy Pattern trong OOP)"""
    
    @abstractmethod
    def calculate_discount(self, subtotal: float, customer: Optional[Customer], item_count: int) -> float:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def get_code(self) -> str:
        pass


class NoDiscountPolicy(DiscountPolicy):
    def calculate_discount(self, subtotal: float, customer: Optional[Customer], item_count: int) -> float:
        return 0.0

    def get_description(self) -> str:
        return "Không áp dụng giảm giá"

    def get_code(self) -> str:
        return "NONE"


class VIPDiscountPolicy(DiscountPolicy):
    def calculate_discount(self, subtotal: float, customer: Optional[Customer], item_count: int) -> float:
        if customer:
            rate = customer.get_discount_rate()
            return subtotal * rate
        return 0.0

    def get_description(self) -> str:
        return "Chiết khấu đặc quyền thành viên VIP"

    def get_code(self) -> str:
        return "VIP_TIER"


class SeasonalPromotionPolicy(DiscountPolicy):
    """Giảm 12% cho mọi đơn hàng từ 250,000 VND"""
    def calculate_discount(self, subtotal: float, customer: Optional[Customer], item_count: int) -> float:
        if subtotal >= 250000.0:
            return subtotal * 0.12
        return 0.0

    def get_description(self) -> str:
        return "Mùa Đọc Sách Tri Thức (-12% cho đơn từ 250.000đ)"

    def get_code(self) -> str:
        return "SEASONAL_12"


class BulkOrderPolicy(DiscountPolicy):
    """Giảm 15% khi mua từ 4 cuốn sách trở lên"""
    def calculate_discount(self, subtotal: float, customer: Optional[Customer], item_count: int) -> float:
        if item_count >= 4:
            return subtotal * 0.15
        return 0.0

    def get_description(self) -> str:
        return "Mua Nhiều Giá Tốt (-15% khi mua từ 4 cuốn trở lên)"

    def get_code(self) -> str:
        return "BULK_15"


# ==========================================
# 5. COMPOSITION: ORDER & INVENTORY
# ==========================================

class OrderItem:
    """Đóng gói từng dòng sản phẩm trong đơn hàng (Composition)"""
    def __init__(self, item: Item, quantity: int):
        if quantity <= 0:
            raise ValueError("Số lượng sách phải lớn hơn 0")
        self._item = item
        self._quantity = quantity
        self._unit_price = item.price

    @property
    def item(self) -> Item:
        return self._item

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def unit_price(self) -> float:
        return self._unit_price

    @property
    def subtotal(self) -> float:
        return self._unit_price * self._quantity

    @property
    def shipping_fee(self) -> float:
        # Tính đa hình: item tự tính shipping
        return self._item.calculate_shipping_fee()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self._item.id,
            "title": self._item.title,
            "author": self._item.author,
            "format": self._item.get_format().value,
            "quantity": self._quantity,
            "unit_price": self._unit_price,
            "subtotal": self.subtotal,
            "shipping_fee": self.shipping_fee
        }


class Order:
    """Đơn hàng nhà sách (Tổng hợp từ OrderItem, Customer và DiscountPolicy)"""
    def __init__(self, order_id: str, customer: Optional[Customer], 
                 discount_policy: DiscountPolicy, payment_method: str = "Tiền mặt",
                 shipping_address: str = "", order_type: str = "ONLINE"):
        self._id = order_id or ("HD-" + datetime.now().strftime("%y%m%d") + "-" + str(uuid.uuid4())[:4].upper())
        self._customer = customer
        self._discount_policy = discount_policy
        self._payment_method = payment_method
        self._shipping_address = shipping_address.strip()
        self._order_type = order_type
        self._items: List[OrderItem] = []
        self._created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._status = OrderStatus.COMPLETED

    @property
    def id(self) -> str:
        return self._id

    @property
    def items(self) -> List[OrderItem]:
        return self._items

    @property
    def total_quantity(self) -> int:
        return sum(it.quantity for it in self._items)

    @property
    def subtotal(self) -> float:
        return sum(it.subtotal for it in self._items)

    @property
    def shipping_fee(self) -> float:
        # Đa hình: Lấy phí ship lớn nhất của các sách vật lý (hoặc 0 nếu toàn EBook/AudioBook)
        shipping_fees = [it.shipping_fee for it in self._items]
        return max(shipping_fees) if shipping_fees else 0.0

    @property
    def discount_amount(self) -> float:
        # Đa hình: Ủy thác tính giảm giá cho Strategy
        return self._discount_policy.calculate_discount(self.subtotal, self._customer, self.total_quantity)

    @property
    def final_total(self) -> float:
        amount = self.subtotal - self.discount_amount + self.shipping_fee
        return max(0.0, amount)

    def add_item(self, item: Item, quantity: int):
        """Thêm sách vào đơn hàng"""
        for it in self._items:
            if it.item.id == item.id:
                new_qty = it.quantity + quantity
                self._items.remove(it)
                self._items.append(OrderItem(item, new_qty))
                return
        self._items.append(OrderItem(item, quantity))

    def complete_order(self) -> bool:
        """Xử lý trừ kho và tích điểm cho khách hàng"""
        for it in self._items:
            if not it.item.reduce_stock(it.quantity):
                raise ValueError(f"Không đủ tồn kho cho cuốn '{it.item.title}'")
        
        if self._customer:
            self._customer.record_purchase(self.final_total)
            
        self._status = OrderStatus.COMPLETED
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "created_at": self._created_at,
            "customer": self._customer.to_dict() if self._customer else None,
            "payment_method": self._payment_method,
            "shipping_address": self._shipping_address,
            "order_type": self._order_type,
            "discount_policy": {
                "code": self._discount_policy.get_code(),
                "description": self._discount_policy.get_description()
            },
            "items": [it.to_dict() for it in self._items],
            "total_quantity": self.total_quantity,
            "subtotal": self.subtotal,
            "discount_amount": self.discount_amount,
            "shipping_fee": self.shipping_fee,
            "final_total": self.final_total,
            "status": self._status.value
        }


class Inventory:
    """Quản lý kho sách (Tính đóng gói và quản lý danh mục sách)"""
    def __init__(self):
        self._items: Dict[str, Item] = {}

    def add_item(self, item: Item):
        self._items[item.id] = item

    def get_item(self, item_id: str) -> Optional[Item]:
        return self._items.get(item_id)

    def remove_item(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def get_all(self) -> List[Item]:
        return list(self._items.values())

    def search(self, query: str = "", category: str = "", fmt: str = "") -> List[Item]:
        results = list(self._items.values())
        if query:
            q = query.lower().strip()
            results = [it for it in results if q in it.title.lower() or q in it.author.lower()]
        if category and category != "ALL":
            results = [it for it in results if it.category.lower() == category.lower()]
        if fmt and fmt != "ALL":
            results = [it for it in results if it.get_format().value == fmt]
        return results

    def get_low_stock_items(self, threshold: int = 5) -> List[PhysicalBook]:
        """Lọc các cuốn sách in có số lượng tồn kho thấp hơn ngưỡng cảnh báo"""
        return [
            it for it in self._items.values() 
            if isinstance(it, PhysicalBook) and it.stock <= threshold
        ]

    def get_categories(self) -> List[str]:
        return sorted(list(set(it.category for it in self._items.values())))


# ==========================================
# 6. FACADE: BOOKSTORE MANAGER (MAIN CONTROLLER)
# ==========================================

class BookstoreManager:
    """
    Facade Pattern: Lớp điều phối trung tâm toàn bộ nhà sách.
    Tích hợp Kho hàng (Inventory), Khách hàng (Customers), Đơn hàng (Orders)
    và lưu trữ dữ liệu bền vững.
    """
    
    def __init__(self, data_file: str = "bookstore_data.json"):
        self.data_file = data_file
        self.inventory = Inventory()
        self.customers: Dict[str, Customer] = {}
        self.orders: List[Order] = []
        
        # Đăng ký các chính sách giảm giá
        self.discount_policies: Dict[str, DiscountPolicy] = {
            "NONE": NoDiscountPolicy(),
            "VIP_TIER": VIPDiscountPolicy(),
            "SEASONAL_12": SeasonalPromotionPolicy(),
            "BULK_15": BulkOrderPolicy(),
        }
        
        # Khởi tạo dữ liệu
        self._load_or_seed()

    def create_book(self, data: Dict[str, Any]) -> Item:
        """Factory Method tạo đối tượng sách dựa trên format (Kế thừa & Đa hình)"""
        fmt = data.get("format", BookFormat.PHYSICAL.value).upper()
        item_id = data.get("id") or str(uuid.uuid4())[:8]
        title = data.get("title", "Sách mới")
        author = data.get("author", "Khuyết danh")
        category = data.get("category", "Tổng hợp")
        price = float(data.get("price", 100000))
        stock = int(data.get("stock", 10))
        isbn = data.get("isbn", f"978-604-{str(uuid.uuid4().int)[:6]}")
        publisher = data.get("publisher", "NXB Trẻ")
        publish_year = int(data.get("publish_year", 2024))
        description = data.get("description", "")

        if fmt == BookFormat.PHYSICAL.value:
            weight = float(data.get("weight_grams", 350))
            shelf = data.get("shelf_location", "Kệ A-01")
            cover = data.get("cover_type", "Bìa mềm")
            book = PhysicalBook(item_id, title, author, category, price, stock, isbn, publisher, publish_year, weight, shelf, cover, description)
        elif fmt == BookFormat.EBOOK.value:
            size = float(data.get("file_size_mb", 15.5))
            file_fmt = data.get("file_format", "PDF")
            link = data.get("download_link", "")
            book = EBook(item_id, title, author, category, price, isbn, publisher, publish_year, size, file_fmt, link, description)
        elif fmt == BookFormat.AUDIOBOOK.value:
            duration = int(data.get("duration_minutes", 420))
            narrator = data.get("narrator", "Giọng đọc chuyên nghiệp")
            audio_url = data.get("sample_audio_url", "")
            book = AudioBook(item_id, title, author, category, price, isbn, publisher, publish_year, duration, narrator, audio_url, description)
        else:
            raise ValueError(f"Định dạng sách không hỗ trợ: {fmt}")

        self.inventory.add_item(book)
        self.save_data()
        return book

    def update_book(self, book_id: str, data: Dict[str, Any]) -> Optional[Item]:
        book = self.inventory.get_item(book_id)
        if not book:
            return None

        if "title" in data: book.title = data["title"]
        if "author" in data: book.author = data["author"]
        if "category" in data: book.category = data["category"]
        if "price" in data: book.price = float(data["price"])
        if "description" in data: book.description = data["description"]
        if "stock" in data and isinstance(book, PhysicalBook):
            book.stock = int(data["stock"])
        if "shelf_location" in data and isinstance(book, PhysicalBook):
            book.shelf_location = data["shelf_location"]

        self.save_data()
        return book

    def delete_book(self, book_id: str) -> bool:
        res = self.inventory.remove_item(book_id)
        if res:
            self.save_data()
        return res

    def restock_book(self, book_id: str, quantity: int) -> bool:
        book = self.inventory.get_item(book_id)
        if book and isinstance(book, PhysicalBook):
            book.restock(quantity)
            self.save_data()
            return True
        return False

    def register_customer(self, name: str, phone: str, email: str, is_vip: bool = False, tier: str = "BRONZE") -> Customer:
        cid = "KH-" + str(uuid.uuid4())[:6].upper()
        if is_vip:
            cust = VIPCustomer(cid, name, phone, email, loyalty_points=50, total_spent=0, tier=VIPTier(tier))
        else:
            cust = Customer(cid, name, phone, email, loyalty_points=0, total_spent=0)
        self.customers[cid] = cust
        self.save_data()
        return cust

    def create_order(self, customer_id: Optional[str], items_data: List[Dict[str, Any]], 
                     discount_code: str = "NONE", payment_method: str = "Tiền mặt",
                     customer_info: Optional[Dict[str, str]] = None,
                     shipping_address: str = "", order_type: str = "ONLINE") -> Order:
        """Tạo đơn hàng áp dụng tính Đa hình và Đóng gói (hỗ trợ cả POS tại quầy và Khách mua Online)"""
        customer = None
        if customer_id:
            customer = self.customers.get(customer_id)
        elif customer_info and customer_info.get("phone"):
            # Tìm khách hàng theo số điện thoại
            phone = customer_info.get("phone", "").strip()
            for c in self.customers.values():
                if c.phone == phone:
                    customer = c
                    break
            # Nếu chưa có thì tự động đăng ký khách hàng mới
            if not customer and customer_info.get("name"):
                customer = self.register_customer(
                    name=customer_info.get("name", "Khách hàng Online"),
                    phone=phone,
                    email=customer_info.get("email", ""),
                    is_vip=False
                )
        
        # Nếu khách là VIP và chọn mã NONE hoặc VIP_TIER thì tự động áp dụng VIPDiscountPolicy
        if customer and customer.get_discount_rate() > 0 and discount_code == "NONE":
            policy = self.discount_policies.get("VIP_TIER", NoDiscountPolicy())
        else:
            policy = self.discount_policies.get(discount_code, NoDiscountPolicy())

        order = Order(
            order_id="",
            customer=customer,
            discount_policy=policy,
            payment_method=payment_method,
            shipping_address=shipping_address,
            order_type=order_type
        )

        for item_info in items_data:
            item_id = item_info["id"]
            qty = int(item_info["quantity"])
            book = self.inventory.get_item(item_id)
            if not book:
                raise ValueError(f"Không tìm thấy sách với ID: {item_id}")
            if isinstance(book, PhysicalBook) and book.stock < qty:
                raise ValueError(f"Sách '{book.title}' chỉ còn {book.stock} cuốn trong kho (bạn đặt {qty})")
            order.add_item(book, qty)

        order.complete_order()
        self.orders.insert(0, order)
        self.save_data()
        return order

    def get_statistics(self) -> Dict[str, Any]:
        """Thống kê tình hình kinh doanh của nhà sách"""
        total_revenue = sum(o.final_total for o in self.orders)
        total_orders = len(self.orders)
        all_books = self.inventory.get_all()
        total_physical_stock = sum(b.stock for b in all_books if isinstance(b, PhysicalBook))
        low_stock_list = self.inventory.get_low_stock_items(threshold=5)

        # Tính sách bán chạy
        sales_counter: Dict[str, Dict[str, Any]] = {}
        for o in self.orders:
            for it in o.items:
                bid = it.item.id
                if bid not in sales_counter:
                    sales_counter[bid] = {
                        "title": it.item.title,
                        "format": it.item.get_format().value,
                        "category": it.item.category,
                        "total_sold": 0,
                        "revenue": 0.0
                    }
                sales_counter[bid]["total_sold"] += it.quantity
                sales_counter[bid]["revenue"] += it.subtotal

        top_sellers = sorted(sales_counter.values(), key=lambda x: x["total_sold"], reverse=True)[:5]

        # Doanh thu theo thể loại
        category_revenue: Dict[str, float] = {}
        for o in self.orders:
            for it in o.items:
                cat = it.item.category
                category_revenue[cat] = category_revenue.get(cat, 0.0) + it.subtotal

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_books_types": len(all_books),
            "total_physical_stock": total_physical_stock,
            "total_customers": len(self.customers),
            "low_stock_count": len(low_stock_list),
            "low_stock_items": [b.to_dict() for b in low_stock_list],
            "top_sellers": top_sellers,
            "category_revenue": category_revenue
        }

    def get_oop_architecture_metadata(self) -> Dict[str, Any]:
        """Mô tả chi tiết kiến trúc OOP và 4 trụ cột để hiển thị trực quan trên giao diện"""
        return {
            "pillars": [
                {
                    "name": "Tính Trừu Tượng (Abstraction)",
                    "description": "Ẩn chi tiết phức tạp, chỉ hiển thị giao diện cần thiết qua các lớp trừu tượng abc.ABC.",
                    "examples": [
                        "Lớp trừu tượng Item định nghĩa khuôn mẫu: calculate_shipping_fee(), to_dict(), get_format()",
                        "Lớp trừu tượng DiscountPolicy định nghĩa calculate_discount(), get_description()",
                        "Lớp trừu tượng Person quản lý thông tin định danh con người"
                    ]
                },
                {
                    "name": "Tính Đóng Gói (Encapsulation)",
                    "description": "Bảo vệ trạng thái nội tại của đối tượng, truy cập qua @property và setter có logic kiểm định.",
                    "examples": [
                        "Thuộc tính _price và _stock được bảo vệ: price.setter ngăn giá âm, stock.setter ngăn tồn kho âm",
                        "Phương thức reduce_stock() và restock() kiểm tra nghiêm ngặt lượng xuất nhập kho",
                        "Customer bảo vệ điểm tích lũy _loyalty_points và doanh số _total_spent"
                    ]
                },
                {
                    "name": "Tính Kế Thừa (Inheritance)",
                    "description": "Tái sử dụng mã nguồn và mở rộng tính năng theo mô hình phân cấp thực thể.",
                    "examples": [
                        "Item -> Book -> PhysicalBook (thêm trọng lượng, vị trí kệ, loại bìa)",
                        "Item -> Book -> EBook (thêm dung lượng file, định dạng PDF/EPUB, link tải)",
                        "Item -> Book -> AudioBook (thêm thời lượng phút, người đọc/narrator)",
                        "Person -> Customer -> VIPCustomer (kế thừa thông tin khách, thêm phân hạng và tỷ lệ giảm giá VIP)"
                    ]
                },
                {
                    "name": "Tính Đa Hình (Polymorphism)",
                    "description": "Các đối tượng khác nhau cùng thực thi một phương thức theo cách riêng phù hợp với bản chất của nó.",
                    "examples": [
                        "calculate_shipping_fee(): PhysicalBook tính theo trọng lượng; EBook & AudioBook tính phí = 0",
                        "DiscountPolicy.calculate_discount(): NoDiscount (0đ), VIPDiscount (5%-20%), Seasonal (-12%), Bulk (-15%)",
                        "Order xử lý tính tiền và chiết khấu một cách đa hình mà không cần kiểm tra kiểu dữ liệu thủ công"
                    ]
                }
            ],
            "classes": [
                {"name": "Item", "type": "Abstract Base Class", "file": "bookstore_oop.py", "parent": "ABC"},
                {"name": "Book", "type": "Base Class", "file": "bookstore_oop.py", "parent": "Item"},
                {"name": "PhysicalBook", "type": "Subclass", "file": "bookstore_oop.py", "parent": "Book"},
                {"name": "EBook", "type": "Subclass", "file": "bookstore_oop.py", "parent": "Book"},
                {"name": "AudioBook", "type": "Subclass", "file": "bookstore_oop.py", "parent": "Book"},
                {"name": "Person", "type": "Abstract Base Class", "file": "bookstore_oop.py", "parent": "ABC"},
                {"name": "Customer", "type": "Class", "file": "bookstore_oop.py", "parent": "Person"},
                {"name": "VIPCustomer", "type": "Subclass", "file": "bookstore_oop.py", "parent": "Customer"},
                {"name": "DiscountPolicy", "type": "Abstract Strategy", "file": "bookstore_oop.py", "parent": "ABC"},
                {"name": "BookstoreManager", "type": "Facade Controller", "file": "bookstore_oop.py", "parent": "object"}
            ]
        }

    def save_data(self):
        """Ghi dữ liệu ra file JSON để đảm bảo tính bền vững (Persistence)"""
        try:
            payload = {
                "books": [b.to_dict() for b in self.inventory.get_all()],
                "customers": [c.to_dict() for c in self.customers.values()],
                "orders": [o.to_dict() for o in self.orders]
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Warning] Không thể lưu file {self.data_file}: {e}")

    def _load_or_seed(self):
        """Đọc file đã lưu hoặc khởi tạo hạt mầm dữ liệu mẫu chuẩn thực tế"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Nạp sách
                for b_data in data.get("books", []):
                    self.create_book(b_data)
                    
                # Nạp khách hàng
                for c_data in data.get("customers", []):
                    is_vip = c_data.get("is_vip", False)
                    cid = c_data.get("id")
                    name = c_data.get("name")
                    phone = c_data.get("phone")
                    email = c_data.get("email")
                    points = c_data.get("loyalty_points", 0)
                    spent = c_data.get("total_spent", 0.0)
                    tier = c_data.get("tier", "STANDARD")
                    if is_vip:
                        cust = VIPCustomer(cid, name, phone, email, points, spent, VIPTier(tier))
                    else:
                        cust = Customer(cid, name, phone, email, points, spent)
                    self.customers[cid] = cust
                    
                # Nạp đơn hàng
                for o_data in data.get("orders", []):
                    cust_info = o_data.get("customer")
                    cust = self.customers.get(cust_info["id"]) if cust_info else None
                    disc_code = o_data.get("discount_policy", {}).get("code", "NONE")
                    policy = self.discount_policies.get(disc_code, NoDiscountPolicy())
                    pm = o_data.get("payment_method", "Tiền mặt")
                    order = Order(order_id=o_data.get("id"), customer=cust, discount_policy=policy, payment_method=pm)
                    order._created_at = o_data.get("created_at", "")
                    
                    for it_data in o_data.get("items", []):
                        book = self.inventory.get_item(it_data.get("item_id"))
                        if book:
                            order._items.append(OrderItem(book, it_data.get("quantity", 1)))
                    self.orders.append(order)
                return
            except Exception as e:
                print(f"[Warning] Lỗi đọc file dữ liệu cũ ({e}), sẽ tạo dữ liệu mẫu...")

        self.seed_sample_data()

    def seed_sample_data(self):
        """Khởi tạo sách thực tế, đa dạng thể loại và định dạng"""
        sample_books = [
            # Sách in PhysicalBook
            {
                "id": "BK-OOP-01",
                "title": "Lập Trình Hướng Đối Tượng Python Nâng Cao",
                "author": "TS. Nguyễn Văn Toàn",
                "category": "Công nghệ & Lập trình",
                "price": 185000,
                "stock": 18,
                "isbn": "978-604-01-2891-2",
                "publisher": "NXB Thông Tin & Truyền Thông",
                "publish_year": 2024,
                "format": BookFormat.PHYSICAL.value,
                "weight_grams": 620,
                "shelf_location": "Kệ IT-03",
                "cover_type": "Bìa mềm",
                "description": "Giáo trình toàn diện về 4 trụ cột OOP, Design Patterns và Best Practices kiến trúc phần mềm trong Python."
            },
            {
                "id": "BK-LIT-02",
                "title": "Dế Mèn Phiêu Lưu Ký (Ấn Bản Đặc Biệt)",
                "author": "Tô Hoài",
                "category": "Văn học Việt Nam",
                "price": 120000,
                "stock": 35,
                "isbn": "978-604-02-1145-0",
                "publisher": "NXB Kim Đồng",
                "publish_year": 2023,
                "format": BookFormat.PHYSICAL.value,
                "weight_grams": 450,
                "shelf_location": "Kệ VH-01",
                "cover_type": "Bìa cứng",
                "description": "Kiệt tác văn học thiếu nhi Việt Nam với các minh họa màu tuyệt đẹp và bài học nhân văn sâu sắc."
            },
            {
                "id": "BK-BIZ-03",
                "title": "Tâm Lý Học Về Tiền (The Psychology of Money)",
                "author": "Morgan Housel",
                "category": "Kinh tế & Tài chính",
                "price": 149000,
                "stock": 4, # Cố ý để < 5 để kích hoạt cảnh báo sắp hết hàng
                "isbn": "978-604-03-9081-4",
                "publisher": "NXB Trẻ",
                "publish_year": 2023,
                "format": BookFormat.PHYSICAL.value,
                "weight_grams": 480,
                "shelf_location": "Kệ KT-02",
                "cover_type": "Bìa mềm",
                "description": "Những bài học vượt thời gian về sự giàu có, lòng tham và hạnh phúc qua lăng kính tâm lý học."
            },
            {
                "id": "BK-LIT-04",
                "title": "Số Đỏ (Tái Bản Minh Họa Nghệ Thuật)",
                "author": "Vũ Trọng Phụng",
                "category": "Văn học Việt Nam",
                "price": 115000,
                "stock": 3, # Low stock alert
                "isbn": "978-604-04-1229-7",
                "publisher": "NXB Văn Học",
                "publish_year": 2022,
                "format": BookFormat.PHYSICAL.value,
                "weight_grams": 390,
                "shelf_location": "Kệ VH-02",
                "cover_type": "Bìa mềm",
                "description": "Tác phẩm trào phúng sắc sảo bậc nhất của văn học hiện thực phê phán Việt Nam thế kỷ 20."
            },
            {
                "id": "BK-SCI-05",
                "title": "Vũ Trụ Trong Vỏ Hạt Dẻ (The Universe in a Nutshell)",
                "author": "Stephen Hawking",
                "category": "Khoa học & Vũ trụ",
                "price": 195000,
                "stock": 12,
                "isbn": "978-604-05-3310-9",
                "publisher": "NXB Trẻ",
                "publish_year": 2022,
                "format": BookFormat.PHYSICAL.value,
                "weight_grams": 540,
                "shelf_location": "Kệ KH-01",
                "cover_type": "Bìa cứng",
                "description": "Khám phá những biên giới mới nhất của vật lý lý thuyết, lỗ đen và thuyết lượng tử."
            },

            # E-Book
            {
                "id": "BK-EBK-06",
                "title": "Clean Code: Sổ Tay Thiết Kế Code Sạch (E-Book)",
                "author": "Robert C. Martin",
                "category": "Công nghệ & Lập trình",
                "price": 89000,
                "isbn": "978-604-06-8821-1",
                "publisher": "NXB Khoa Học & Kỹ Thuật",
                "publish_year": 2024,
                "format": BookFormat.EBOOK.value,
                "file_size_mb": 12.8,
                "file_format": "PDF",
                "download_link": "https://bookstore.vn/download/cleancode_vi.pdf",
                "description": "Bản quyền điện tử hướng dẫn quy chuẩn viết code thanh lịch, dễ bảo trì và mở rộng."
            },
            {
                "id": "BK-EBK-07",
                "title": "Deep Work: Làm Ra Làm, Chơi Ra Chơi (E-Book)",
                "author": "Cal Newport",
                "category": "Kỹ năng sống",
                "price": 75000,
                "isbn": "978-604-07-4491-3",
                "publisher": "NXB Lao Động",
                "publish_year": 2023,
                "format": BookFormat.EBOOK.value,
                "file_size_mb": 8.4,
                "file_format": "EPUB",
                "download_link": "https://bookstore.vn/download/deepwork.epub",
                "description": "Chiến lược rèn luyện sự tập trung cao độ trong thế giới số đầy xao nhãng."
            },

            # AudioBook
            {
                "id": "BK-AUD-08",
                "title": "Đắc Nhân Tâm (Bản Audio Book Thuyết Minh Truyền Cảm)",
                "author": "Dale Carnegie",
                "category": "Kỹ năng sống",
                "price": 99000,
                "isbn": "978-604-08-9901-5",
                "publisher": "First News - Trí Việt",
                "publish_year": 2024,
                "format": BookFormat.AUDIOBOOK.value,
                "duration_minutes": 380,
                "narrator": "NSƯT Hà Phương",
                "sample_audio_url": "https://bookstore.vn/audio/samples/dac_nhan_tam.mp3",
                "description": "Bản thu âm chất lượng phòng thu 320kbps với giọng đọc truyền cảm lay động lòng người."
            }
        ]

        for b in sample_books:
            self.create_book(b)

        # Khách hàng mẫu
        c1 = VIPCustomer("KH-VIP01", "Nguyễn Thành Nam", "0912345678", "nam.nt@example.com", loyalty_points=240, total_spent=4200000, tier=VIPTier.SILVER)
        c2 = VIPCustomer("KH-VIP02", "Trần Mai Phương", "0987654321", "phuong.tm@example.com", loyalty_points=520, total_spent=9500000, tier=VIPTier.GOLD)
        c3 = Customer("KH-REG03", "Lê Hoàng Quân", "0905123987", "quan.lh@example.com", loyalty_points=45, total_spent=450000)
        c4 = Customer("KH-REG04", "Vũ Minh Anh", "0934112233", "minhanh.vu@example.com", loyalty_points=80, total_spent=800000)
        
        for c in [c1, c2, c3, c4]:
            self.customers[c.id] = c

        # Đơn hàng mẫu ban đầu
        try:
            o1 = self.create_order(
                customer_id="KH-VIP01",
                items_data=[
                    {"id": "BK-OOP-01", "quantity": 1},
                    {"id": "BK-EBK-06", "quantity": 1}
                ],
                discount_code="VIP_TIER",
                payment_method="Chuyển khoản QR"
            )
            o2 = self.create_order(
                customer_id="KH-REG03",
                items_data=[
                    {"id": "BK-LIT-02", "quantity": 2}
                ],
                discount_code="NONE",
                payment_method="Tiền mặt"
            )
            o3 = self.create_order(
                customer_id="KH-VIP02",
                items_data=[
                    {"id": "BK-BIZ-03", "quantity": 1},
                    {"id": "BK-AUD-08", "quantity": 1},
                    {"id": "BK-SCI-05", "quantity": 1}
                ],
                discount_code="VIP_TIER",
                payment_method="Thẻ tín dụng"
            )
        except Exception as err:
            print(f"[Seed] Lỗi tạo đơn hàng mẫu: {err}")

        self.save_data()
