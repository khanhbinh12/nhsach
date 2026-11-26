"""Nguồn ngày giờ có thể thay thế trong bài kiểm thử."""
from datetime import datetime


class DongHo:
    def bay_gio(self):
        return datetime.now()

    def hom_nay(self):
        return self.bay_gio().date()
