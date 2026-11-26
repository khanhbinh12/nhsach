class LoiNghiepVu(ValueError):
    """Lỗi dữ liệu hoặc thao tác có thể hiển thị cho người dùng."""


class LoiTruong(LoiNghiepVu):
    def __init__(self, **loi_truong):
        super().__init__(next(iter(loi_truong.values())))
        self.loi_truong = loi_truong


class KhongTimThay(LoiNghiepVu):
    pass


class HetHang(LoiNghiepVu):
    pass
