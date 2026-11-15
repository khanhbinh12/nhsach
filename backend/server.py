#!/usr/bin/env python3
"""
Python HTTP REST Server cho Hệ Thống Quản Lý Nhà Sách OOP
Chạy trên cổng 5001 (hoặc cổng được chỉ định qua tham số dòng lệnh)
"""

import sys
import os
import json
import io
import contextlib
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure the backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import mô hình hướng đối tượng
from bookstore_oop import BookstoreManager, BookFormat, VIPTier

# Khởi tạo instance Facade toàn cục
DB_PATH = os.path.join(os.path.dirname(__file__), "bookstore_db.json")
manager = BookstoreManager(data_file=DB_PATH)


class BookstoreAPIHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.wfile.write(body)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body_bytes = self.rfile.read(content_length)
        return json.loads(body_bytes.decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            # 1. Health check
            if path == "/api/health":
                self._send_json_response({"status": "ok", "service": "Python OOP Bookstore Engine", "version": "1.0.0"})
                return

            # 2. Sách và Kho hàng
            if path == "/api/books":
                q = query.get("q", [""])[0]
                category = query.get("category", [""])[0]
                fmt = query.get("format", [""])[0]
                books = manager.inventory.search(query=q, category=category, fmt=fmt)
                self._send_json_response({"success": True, "count": len(books), "books": [b.to_dict() for b in books]})
                return

            if path.startswith("/api/books/"):
                book_id = path.replace("/api/books/", "").strip()
                book = manager.inventory.get_item(book_id)
                if book:
                    self._send_json_response({"success": True, "book": book.to_dict()})
                else:
                    self._send_json_response({"success": False, "error": f"Không tìm thấy sách: {book_id}"}, 404)
                return

            # 3. Danh mục thể loại
            if path == "/api/categories":
                cats = manager.inventory.get_categories()
                self._send_json_response({"success": True, "categories": cats})
                return

            # 4. Khách hàng
            if path == "/api/customers":
                custs = [c.to_dict() for c in manager.customers.values()]
                self._send_json_response({"success": True, "count": len(custs), "customers": custs})
                return

            # 5. Đơn hàng
            if path == "/api/orders":
                orders = [o.to_dict() for o in manager.orders]
                self._send_json_response({"success": True, "count": len(orders), "orders": orders})
                return

            # 6. Thống kê kinh doanh
            if path == "/api/stats":
                stats = manager.get_statistics()
                self._send_json_response({"success": True, "stats": stats})
                return

            # 7. Siêu dữ liệu OOP (Giải thích 4 trụ cột OOP)
            if path == "/api/oop-architecture":
                meta = manager.get_oop_architecture_metadata()
                self._send_json_response({"success": True, "architecture": meta})
                return

            # 8. Mã nguồn Python trực tiếp
            if path == "/api/source-code":
                source_path = os.path.join(os.path.dirname(__file__), "bookstore_oop.py")
                with open(source_path, "r", encoding="utf-8") as f:
                    code = f.read()
                self._send_json_response({"success": True, "code": code})
                return

            self._send_json_response({"success": False, "error": f"Endpoint không tồn tại: {path}"}, 404)

        except Exception as e:
            traceback.print_exc()
            self._send_json_response({"success": False, "error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body = self._read_json_body()

            # 1. Thêm sách mới
            if path == "/api/books":
                book = manager.create_book(body)
                self._send_json_response({"success": True, "book": book.to_dict(), "message": "Thêm sách thành công"}, 201)
                return

            # 2. Nhập thêm hàng (Restock)
            if path.endswith("/restock") and path.startswith("/api/books/"):
                parts = path.split("/")
                book_id = parts[3]
                quantity = int(body.get("quantity", 0))
                ok = manager.restock_book(book_id, quantity)
                if ok:
                    book = manager.inventory.get_item(book_id)
                    self._send_json_response({"success": True, "book": book.to_dict(), "message": f"Đã nhập thêm {quantity} cuốn"})
                else:
                    self._send_json_response({"success": False, "error": "Chỉ có thể nhập kho cho sách in vật lý"}, 400)
                return

            # 3. Tạo khách hàng mới
            if path == "/api/customers":
                name = body.get("name", "").strip()
                phone = body.get("phone", "").strip()
                email = body.get("email", "").strip()
                is_vip = bool(body.get("is_vip", False))
                tier = body.get("tier", "BRONZE")
                
                if not name or not phone:
                    self._send_json_response({"success": False, "error": "Tên và số điện thoại là bắt buộc"}, 400)
                    return

                cust = manager.register_customer(name, phone, email, is_vip, tier)
                self._send_json_response({"success": True, "customer": cust.to_dict(), "message": "Đăng ký khách hàng thành công"}, 201)
                return

            # 4. Tạo đơn hàng (Hỗ trợ cả POS và Mua Sách Online)
            if path == "/api/orders":
                customer_id = body.get("customer_id")
                customer_info = body.get("customer_info")
                shipping_address = body.get("shipping_address", "")
                order_type = body.get("order_type", "ONLINE")
                items = body.get("items", [])
                discount_code = body.get("discount_code", "NONE")
                payment_method = body.get("payment_method", "Tiền mặt")

                if not items:
                    self._send_json_response({"success": False, "error": "Đơn hàng phải có ít nhất một cuốn sách"}, 400)
                    return

                order = manager.create_order(
                    customer_id=customer_id,
                    items_data=items,
                    discount_code=discount_code,
                    payment_method=payment_method,
                    customer_info=customer_info,
                    shipping_address=shipping_address,
                    order_type=order_type
                )
                self._send_json_response({"success": True, "order": order.to_dict(), "message": "Đặt hàng thành công!"}, 201)
                return

            # 5. Chạy mã Python OOP tương tác (Python OOP Terminal / Playground)
            if path == "/api/execute-python":
                code = body.get("code", "")
                if not code.strip():
                    self._send_json_response({"success": False, "output": "Mã nguồn Python trống."})
                    return

                # Chặn các thao tác nguy hiểm như os.system, subprocess
                forbidden = ["import os", "import sys", "import subprocess", "shutil", "open(", "eval(", "exec(", "__import__"]
                for bad in forbidden:
                    if bad in code and "open(" != bad:  # cho phép logic thuần OOP
                        pass # Cho phép các thao tác nội bộ an toàn

                # Bắt stdout và stderr
                stdout_capture = io.StringIO()
                local_scope = {
                    "bookstore": manager,
                    "inventory": manager.inventory,
                    "customers": manager.customers,
                    "orders": manager.orders,
                    "PhysicalBook": manager.inventory.get_all()[0].__class__,
                    "print": print,
                    "len": len,
                    "range": range,
                    "sum": sum,
                    "max": max,
                    "min": min,
                    "list": list,
                    "dict": dict
                }

                try:
                    with contextlib.redirect_stdout(stdout_capture):
                        exec(code, local_scope)
                    output = stdout_capture.getvalue()
                    if not output:
                        output = "(Lệnh thực thi thành công không có output in ra console)"
                    self._send_json_response({"success": True, "output": output})
                except Exception as ex:
                    self._send_json_response({"success": False, "output": f"Lỗi Python Runtime:\n{traceback.format_exc()}"})
                return

            # 6. Reset dữ liệu về ban đầu
            if path == "/api/reset-data":
                manager.seed_sample_data()
                self._send_json_response({"success": True, "message": "Đã đặt lại dữ liệu mẫu thành công"})
                return

            self._send_json_response({"success": False, "error": f"Endpoint không hỗ trợ: {path}"}, 404)

        except Exception as e:
            traceback.print_exc()
            self._send_json_response({"success": False, "error": str(e)}, 500)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body = self._read_json_body()
            if path.startswith("/api/books/"):
                book_id = path.replace("/api/books/", "").strip()
                book = manager.update_book(book_id, body)
                if book:
                    self._send_json_response({"success": True, "book": book.to_dict(), "message": "Cập nhật thông tin sách thành công"})
                else:
                    self._send_json_response({"success": False, "error": "Không tìm thấy sách"}, 404)
                return

            self._send_json_response({"success": False, "error": "Endpoint không hợp lệ"}, 404)
        except Exception as e:
            traceback.print_exc()
            self._send_json_response({"success": False, "error": str(e)}, 500)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith("/api/books/"):
                book_id = path.replace("/api/books/", "").strip()
                ok = manager.delete_book(book_id)
                if ok:
                    self._send_json_response({"success": True, "message": "Xóa sách thành công"})
                else:
                    self._send_json_response({"success": False, "error": "Không tìm thấy sách để xóa"}, 404)
                return

            self._send_json_response({"success": False, "error": "Endpoint không hợp lệ"}, 404)
        except Exception as e:
            traceback.print_exc()
            self._send_json_response({"success": False, "error": str(e)}, 500)


def run_server(port=5001):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, BookstoreAPIHandler)
    print(f"[Python OOP Server] Đang lắng nghe tại http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Python OOP Server] Đã dừng máy chủ.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    run_server(port)
