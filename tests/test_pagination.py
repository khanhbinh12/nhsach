"""Kiểm thử phân trang."""

import unittest

from bookstore.services import Bookstore
from bookstore.storage import InMemoryStorage
from bookstore.web import create_app
from bookstore.web.pagination import Paginator


class PaginatorTest(unittest.TestCase):
    def test_slices_and_counts(self):
        page = Paginator(10).page(list(range(95)), 3)
        self.assertEqual(list(page.items), list(range(20, 30)))
        self.assertEqual((page.pages, page.first_index, page.last_index), (10, 21, 30))
        self.assertTrue(page.has_prev and page.has_next)

    def test_invalid_or_out_of_range_page_is_clamped(self):
        paginator = Paginator(10)
        self.assertEqual(paginator.page(list(range(95)), "abc").number, 1)
        self.assertEqual(paginator.page(list(range(95)), -4).number, 1)
        self.assertEqual(paginator.page(list(range(95)), 999).number, 10)
        empty = paginator.page([], 3)
        self.assertEqual((empty.number, empty.pages, empty.first_index), (1, 1, 0))

    def test_window_with_gaps(self):
        page = Paginator(10).page(list(range(400)), 20)
        self.assertEqual(page.window(), [1, None, 18, 19, 20, 21, 22, None, 40])
        self.assertEqual(Paginator(10).page(list(range(30)), 1).window(), [1, 2, 3])


class PaginatedPagesTest(unittest.TestCase):
    def test_catalog_is_paginated_and_keeps_filters(self):
        store = Bookstore(InMemoryStorage())
        for i in range(30):
            store.inventory.create({"format": "PHYSICAL", "title": f"Sách {i}", "author": "A", "price": 1000,
                                    "stock": 1, "category": "Tham khảo"})
        client = create_app(store, testing=True).test_client()
        html = client.get("/?the-loai=Tham+kh%E1%BA%A3o&trang=2").get_data(as_text=True)
        self.assertIn("13–24 / 30", html)
        self.assertIn("the-loai=Tham", html)  # link sang trang khác vẫn giữ bộ lọc thể loại
        self.assertEqual(html.count('class="book-card"'), 12)


if __name__ == "__main__":
    unittest.main()
