# Nhà Sách Trí Tri – Web bán sách + Kho E-Book hội viên

Đồ án môn **Phát triển ứng dụng hướng đối tượng** – viết bằng **Python** (Flask) theo hướng đối tượng.

## Mô hình kinh doanh

| Nguồn thu | Khách nhận được | Ghi chú |
|---|---|---|
| **Bán sách giấy** (chính) | Đặt hàng online, giao tận nhà, nhập mã giảm giá | Chờ xử lý → Đang giao → Hoàn tất; hủy đơn tự hoàn kho |
| **Hội viên E-Book** 100.000đ / 365 ngày (phụ) | Xem link Google Drive chứa toàn bộ E-Book | Khách chuyển khoản → admin xác nhận → tự kích hoạt |
| **Xem quảng cáo** (phụ) | Không mở khóa gì – chỉ để ủng hộ web | Phải xem đủ thời lượng mới tính lượt (mô phỏng) |

## Chạy chương trình

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt   # Flask, waitress (máy chủ chạy thật), Pillow (xử lý ảnh bìa)
python run.py                     # mở http://127.0.0.1:5000 (chạy bằng waitress; BOOKSTORE_DEV=1 để dùng server Flask)
python -m unittest discover -s tests -t . -v   # chạy 115 bài kiểm thử
```

Tài khoản demo: **admin / admin123** (quản trị) · **nam.nt@example.com / 123456** (khách đang là hội viên).
Dữ liệu lưu trong SQLite `data/bookstore.db`, ảnh bìa ở `data/uploads/covers/` (muốn dùng file JSON: đặt biến môi trường `BOOKSTORE_STORAGE=json`). Vào **Quản trị → Cấu hình → Đặt lại dữ liệu** để làm mới. Log (lỗi, đăng nhập sai, thao tác quản trị) ghi tại `data/logs/bookstore.log`. Mã giảm giá mẫu: `TRITRI10`, `GIAM30K`.

## Cấu trúc mã nguồn

```
bookstore/
├── models/            Tầng nghiệp vụ
│   ├── product.py     Product → Book → PhysicalBook / EBook; MembershipPlan; ProductFactory
│   ├── person.py      Person → Customer → VIPCustomer; CustomerFactory
│   ├── account.py     Account → CustomerAccount / AdminAccount; PasswordHasher
│   ├── discount.py    DiscountPolicy (Strategy) + DiscountRegistry.best_for()
│   ├── membership.py  EBookMembership, EBookVault (kiểm soát quyền xem link Drive)
│   ├── order.py       Cart, OrderLine, Order
│   ├── tracking.py    Trackable – tự đánh dấu đối tượng đã thay đổi
│   ├── identifiers.py IdGenerator – sinh mã không trùng
│   ├── text.py        slugify – đường dẫn thân thiện (/sach/BK-OOP-01/lap-trinh-huong-doi-tuong…)
│   ├── order_state.py OrderState (State) → PendingState / ShippingState / CompletedState / CancelledState
│   ├── voucher.py     Voucher → PercentVoucher / FixedAmountVoucher
│   └── ads.py         AdSession, AdSettings, AdLedger
├── services/          Tầng dịch vụ
│   ├── events.py      OrderListener (Observer)
│   ├── inventory.py, customers.py, accounts.py, orders.py, membership.py, ads.py, reports.py
│   ├── vouchers.py    VoucherService (cũng là OrderListener: hủy đơn thì hoàn lượt dùng mã)
│   ├── login_throttle.py LoginThrottle – chống dò mật khẩu (5 lần sai/tài khoản, 20 lần sai/IP trong 15 phút)
│   ├── unit_of_work.py UnitOfWork – gom thay đổi sau mỗi lệnh, ghi một lần
│   ├── media.py       CoverImageStore – kiểm tra ảnh thật (Pillow), lưu ảnh lớn + ảnh thu nhỏ WEBP
│   ├── bookstore.py   Facade Bookstore – tầng web chỉ làm việc với lớp này
│   └── seed.py        Dữ liệu mẫu
├── storage.py         DataStorage → InMemoryStorage, FileStorage → JsonFileStorage / SqliteStorage; ChangeSet
└── web/               Tầng giao diện Flask
    ├── views/         shop, accounts, library (Kho E-Book), support (quảng cáo), admin
    ├── forms.py       ProductForm → PhysicalBookForm / EBookForm
    ├── session_cart.py, security.py (CSRF + SecurityHeaders/CSP), context.py (phân quyền), pagination.py
    ├── static/app.js  JavaScript duy nhất (hộp xác nhận, đếm ngược quảng cáo) – CSP chặn mọi inline script
    ├── performance.py StaticAssets (lưu đệm CSS 1 năm, ?v=<băm>) · GzipCompression (nén HTML)
    └── templates/, static/
tests/                 115 bài kiểm thử (model, dịch vụ, web, lưu trữ, phân trang, hiệu năng, bảo mật)
```

## Áp dụng OOP

| Nguyên lý | Thể hiện trong mã |
|---|---|
| **Trừu tượng** | `Product`, `Book`, `Person`, `Account`, `DiscountPolicy`, `ConditionalPercentDiscount`, `Voucher`, `OrderState`, `OrderListener`, `DataStorage`, `FileStorage`, `ProductForm` là lớp trừu tượng (`ABC` + `@abstractmethod`). |
| **Đóng gói** | Thuộc tính `_private` + `@property`, setter kiểm tra dữ liệu; mật khẩu chỉ lưu dạng băm; `EBookVault` chỉ trả link Drive khi khách còn hạn; `Order` chỉ đổi trạng thái qua `complete()` / `cancel()`. |
| **Kế thừa** | `Product → Book → PhysicalBook/EBook`, `Person → Customer → VIPCustomer`, `Account → CustomerAccount/AdminAccount`, `DiscountPolicy → ConditionalPercentDiscount → SeasonalPromotion/BulkOrderDiscount`, `DiscountPolicy → Voucher → PercentVoucher/FixedAmountVoucher`, `OrderState → 4 trạng thái`, `DataStorage → FileStorage → JsonFileStorage/SqliteStorage`. |
| **Đa hình** | `purchasable`, `shipping_fee()`, `take_from_stock()`, `return_to_stock()`, `restock()` theo loại sách; `calculate()` theo chính sách giảm giá; `tier`, `discount_rate`, `_points_for()` theo loại khách; `is_admin`, `home_endpoint` theo loại tài khoản; `ship()`/`complete()`/`cancel()`/`actions()`/`hint()` theo trạng thái đơn; `order_completed()` theo từng listener; `load()`/`save()` theo cách lưu trữ. |

**Mẫu thiết kế:** Factory + Registry (`ProductFactory`, `CustomerFactory`, `Account.__init_subclass__`),
Strategy (`DiscountPolicy`), State (`OrderState`), Observer (`OrderListener`), Facade (`Bookstore`), Template Method
(`Customer.record_purchase`), Adapter (`SessionCart`), Repository (`DataStorage`), Unit of Work (`UnitOfWork` + `Trackable`: chỉ ghi đối tượng đã thay đổi), Application Factory (`create_app`).

## Ghi chú

- Thanh toán và quảng cáo là **mô phỏng**; link Google Drive trong dữ liệu mẫu là link giả.
- Khi nộp bài, không cần gửi kèm `.venv/` và `data/` (tự tạo lại khi cài đặt và chạy).

## Hiệu năng (đo với ~2.000 sách, ~3.000 đơn)

| | Trước tối ưu | Sau (phân trang + Unit of Work) |
|---|---|---|
| Trang chủ | 167 ms · 1,5 MB | 7 ms · 14 KB |
| Trang đơn hàng (quản trị) | 369 ms · 4,1 MB | 9 ms · 37 KB |
| Một lệnh ghi (nhập kho) | 111 ms | 18 ms (chỉ ghi 1 dòng) |
| Trang chủ qua mạng (gzip) | 10 KB | 2 KB |
| Ảnh bìa trong danh sách | ảnh gốc ~1,5 MB | ảnh thu nhỏ ~6 KB |
