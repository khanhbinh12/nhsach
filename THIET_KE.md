# Thiết kế — Nhà Sách Tri Thức

Web bán sách trực tuyến viết bằng Python 3.12 và Flask, dùng SQLite. Code tổ chức theo hướng đối tượng.

## 1. Kiến trúc

Code chia thành 4 tầng. Mỗi tầng chỉ gọi tầng ngay dưới nó.

| Tầng | Module | Vai trò |
| --- | --- | --- |
| Mô hình | `nha_sach/mo_hinh.py` | Các lớp nghiệp vụ và quy tắc. Không phụ thuộc Flask hay SQLite |
| Kho | `nha_sach/kho.py` | Toàn bộ câu SQL. Trả về đối tượng của mô hình |
| Dịch vụ | `nha_sach/dich_vu.py` | Ghép các quy tắc thành tình huống sử dụng (đặt hàng, duyệt review…). Chạy trong giao dịch |
| Web | `nha_sach/web.py`, `web_cua_hang.py`, `web_quan_ly.py` | Hai Blueprint `cua_hang` và `quan_ly`. Chỉ đọc request, gọi dịch vụ, dựng template |

Bộ kiểm `tests/test_kien_truc.py` dùng AST để giữ ranh giới này:
- chỉ `kho.py` được chứa SQL;
- `mo_hinh.py` và `dich_vu.py` không import Flask;
- web không rẽ nhánh theo loại thanh toán;
- mỗi hàm không quá 60 dòng, mỗi lớp không quá 10 phương thức công khai;
- giới hạn số câu SQL trên mỗi trang.

## 2. Hướng đối tượng

- **Đóng gói.**
  - `DonHang` giữ quy tắc chuyển trạng thái (`buoc_hop_le()`, `chuyen_sang()`).
  - `MaGiamGia` tự trả lời mã có dùng được không và vì sao.
  - `ChinhSachGiaoHang` giữ phí giao và ngưỡng miễn phí.
- **Trừu tượng và đa hình.** Hai cây kế thừa có nghiệp vụ thật. Chỗ gọi không cần biết đang dùng lớp con nào.
  ```
  PhuongThucThanhToan (ABC)            QuyTacGiamGia (ABC)
  ├── ThanhToanCOD                     ├── GiamPhanTram
  └── ThanhToanChuyenKhoan             └── GiamSoTien
  ```
  - `ThanhToanCOD` cho giao trước, thu tiền khi giao. `ThanhToanChuyenKhoan` phải trả trước mới được giao, có mã QR, và phải hoàn tiền khi hủy.
  - Hai lớp giảm giá tự tính số tiền giảm theo cách riêng của mình.
- **Kế thừa.**
  - Lỗi nghiệp vụ: `LoiNghiepVu`, với các lớp con `LoiTruong`, `KhongTimThay`, `HetHang`.
  - Dịch vụ: các lớp con của `DichVu`. `DichVuCuaHang` và `DichVuQuanLy` là facade gom các dịch vụ nhỏ.
- **Đối tượng giá trị.**
  - `BiaSach`: bìa tự vẽ, chọn màu chữ đạt tương phản WCAG.
  - `SoDienThoai`: chuẩn hóa số điện thoại Việt Nam.
  - `XemGio`: trạng thái giỏ hàng để hiển thị.
- **Tiêm phụ thuộc.** `create_app()` nhận sẵn dịch vụ và đồng hồ (`DongHo`), nên test chạy được với bản giả.

## 3. Dữ liệu

SQLite chạy ở chế độ WAL. Lược đồ được nâng cấp theo phiên bản, do `DiChuyenLuocDo` quản lý qua `PRAGMA user_version`.

Các bảng chính:
- `sach`, `danh_muc`;
- `khach_hang`;
- `don_hang`, `muc_don`;
- `ma_giam_gia`;
- `danh_gia` (đánh giá của khách đã mua);
- `bai_review` (review của nhà sách, trạng thái nháp hoặc đã duyệt).

Dữ liệu mẫu nằm trong `du_lieu/`: 50 sách, 14 thể loại, 20 ảnh bìa, 20 review (6 bài đã duyệt). Lớp `NapDuLieuMau` nạp dữ liệu này khi CSDL còn trống.

## 4. Chức năng và route

**Khách**
| Chức năng | Route |
| --- | --- |
| Trang chủ: sách nổi bật, Bán chạy (theo số bán thật 30 ngày), Ưu đãi, Góc review, Sách mới, Vừa xem | `/` |
| Danh sách sách: tìm theo tên, tác giả, NXB (xếp theo độ khớp); lọc theo thể loại, giá, giảm giá, còn hàng, có review; nhiều cách sắp xếp | `/sach` |
| Gợi ý khi gõ (JSON) | `/api/goi-y` |
| Chi tiết sách: review của nhà sách, đánh giá, sách cùng tác giả, sách cùng thể loại | `/sach/<ma>`, `POST /sach/<ma>/danh-gia` |
| Giỏ hàng, mã giảm giá | `/gio`, `/gio/them`, `/gio/sua`, `/gio/ma-giam-gia`, `/gio/bo-ma` |
| Đặt hàng (COD hoặc chuyển khoản QR), áp mã ngay tại trang | `/dat-hang` |
| Xem đơn, tra cứu, hủy đơn | `/don/<ma>`, `/tra-cuu`, `POST /don/<ma>/huy` |
| Tài khoản | `/dang-ky`, `/dang-nhap`, `/dang-xuat`, `/tai-khoan`, `/tai-khoan/ho-so` |

**Quản lý** (`/quan-ly`)
- Tổng quan doanh thu (biểu đồ và bảng số liệu).
- Sách: thêm, sửa, ngừng bán, mở bán lại.
- Thể loại.
- Đơn hàng: tìm kiếm, xác nhận thanh toán, chuyển trạng thái, hủy kèm hoàn tiền, in hóa đơn.
- Mã giảm giá.
- Khách hàng.
- Đánh giá: ẩn.
- Review của nhà sách: viết, sửa, duyệt.
- Xuất CSV đơn hàng và doanh thu.

## 5. Bảo mật (ở mức đồ án)

- CSRF cho mọi form POST.
- Mật khẩu được băm.
- Giới hạn số lần đăng nhập sai và tra cứu sai.
- Đăng xuất thì vô hiệu phiên cũ.
- Phân quyền xem và hủy đơn.
- Truy vấn SQL dùng tham số.
- Template tự thoát ký tự (autoescape).
- Kiểm loại file ảnh tải lên.
- Chặn chèn công thức vào file CSV.
- Header `nosniff`, `X-Frame-Options`, `Referrer-Policy`.

## 6. Kiểm thử

Chạy toàn bộ bằng một lệnh: `python kiem/tat_ca.py --tich-hop`. Lệnh này gồm:
- test Python: nghiệp vụ, kiến trúc, hợp đồng template, dữ liệu, tích hợp;
- dựng thử mọi template;
- kiểm giao diện chạy bằng Edge headless:
  - font tiếng Việt;
  - tràn ngang ở 360, 400, 768 và 1440px;
  - tương phản màu WCAG AA;
  - vùng chạm 44px;
  - token cỡ chữ và bo góc;
  - bố cục màn hình đầu.
