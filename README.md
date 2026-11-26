# Nhà Sách Tri Thức

Web trình diễn bán và quản lý sách, viết bằng Python 3.12, Flask và SQLite.

## Cài đặt và chạy trên Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Mở `http://127.0.0.1:5000`. Lần đầu chạy, ứng dụng nạp 50 đầu sách thuộc 14 thể loại, đơn mẫu và 20 review (6 bài đã duyệt). Vào `/quan-ly/dang-nhap` với mật khẩu thử `admin`. Khách có thể tự đăng ký hoặc mua nhanh không cần tài khoản.

| Biến môi trường | Tác dụng |
|---|---|
| `PORT` | Cổng, mặc định 5000 |
| `NHA_SACH_DB` | Đường dẫn file SQLite, mặc định `nha_sach.db` |
| `NHA_SACH_KHOA` | Khóa ký phiên. Mặc định dùng khóa tạo lần đầu trong `instance/khoa_bi_mat` |
| `NHA_SACH_MAT_KHAU` | Mật khẩu quản lý |
| `NHA_SACH_TEN`, `NHA_SACH_DIA_CHI`, `NHA_SACH_DIEN_THOAI` | Thông tin cửa hàng trên hóa đơn |
| `NHA_SACH_NGAN_HANG_BIN`, `NHA_SACH_NGAN_HANG_TEN`, `NHA_SACH_NGAN_HANG_SO_TK`, `NHA_SACH_NGAN_HANG_CHU_TK` | Thông tin QR. Khi thiếu cấu hình, ứng dụng hiển thị mã mô phỏng |
| `NHA_SACH_TEMPLATE_TEST` | Thư mục template tùy chọn khi chạy kiểm tích hợp |
| `NHA_SACH_TICH_HOP` | Đặt thành `1` để yêu cầu template thật khi chạy unittest |
| `EDGE_EXE` | Đường dẫn Edge tùy chọn cho kiểm giao diện |

Mật khẩu mặc định phục vụ trình diễn trên localhost. Bộ đếm thử và nonce quản lý được lưu trong tiến trình Flask, nên khởi động lại tiến trình sẽ đăng xuất quản lý.

## Kịch bản demo 5 phút

1. Ở trang chủ, gõ `de men` và chọn sách trong gợi ý. Bấm **Mua ngay**, tăng giỏ lên hai cuốn nếu cần, rồi áp mã `CHAOHE`. Kiểm tra thông tin đã nhập vẫn còn, đặt hàng và lưu mã tra cứu. Mở cửa sổ riêng để tra bằng mã đơn và số điện thoại.
2. Đăng ký một tài khoản khách, đăng nhập và mua một cuốn. Chọn chuyển khoản nếu muốn trình diễn bước xác nhận tiền bằng dữ liệu mô phỏng.
3. Trong **Quản lý → Đơn hàng**, mở đơn, xác nhận tiền, chuyển trạng thái đến hoàn thành và mở hóa đơn. Tải CSV đơn hàng hoặc doanh thu từ trang quản lý.
4. Quay lại tài khoản khách, mở cuốn vừa mua và gửi đánh giá sao. Trong **Quản lý → Review**, viết một bài nháp cho sách chưa có review hoặc duyệt một bài nháp mẫu, rồi tải lại trang chi tiết sách.

Có thể nhập thêm review nháp cho các sách chưa có review từ JSON hoặc Markdown:

```powershell
.\.venv\Scripts\python.exe -m tools.nhap_review .\review-moi.json --db .\nha_sach.db
```

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest
.\.venv\Scripts\python.exe kiem/tat_ca.py
.\.venv\Scripts\python.exe kiem/tat_ca.py --tich-hop
```

Lệnh cuối yêu cầu nhánh đã ghép đủ Python, template, CSS và kiểm giao diện. Kiểm tràn ngang dùng Microsoft Edge headless.
