"""Kiểm thử các lớp model: trừu tượng, đóng gói, kế thừa, đa hình."""

import unittest
from datetime import date, datetime, timedelta

from bookstore.exceptions import (
    AccessDeniedError,
    AuthenticationError,
    OutOfStockError,
    UnsupportedOperationError,
    ValidationError,
)
from bookstore.models import (
    Account,
    AdLedger,
    AdminAccount,
    Book,
    BulkOrderDiscount,
    Cart,
    Customer,
    CustomerAccount,
    CustomerFactory,
    DiscountPolicy,
    DiscountRegistry,
    EBook,
    EBookMembership,
    EBookVault,
    FixedAmountVoucher,
    MembershipPlan,
    NoDiscount,
    Order,
    OrderAction,
    OrderLine,
    OrderState,
    OrderStatus,
    OrderType,
    PasswordHasher,
    PercentVoucher,
    Person,
    PhysicalBook,
    Product,
    ProductFactory,
    SeasonalPromotion,
    VIPCustomer,
    VIPDiscount,
    VIPTier,
    Voucher,
)

BOOK = {"title": "Sách thử", "author": "Tác giả", "category": "Thử nghiệm"}


def physical(**overrides):
    return PhysicalBook(**{**BOOK, "price": 100_000, "stock": 5, "weight_grams": 450, **overrides})


def ebook(**overrides):
    return EBook(**{**BOOK, "drive_link": "https://drive.google.com/x", **overrides})


class AbstractionTest(unittest.TestCase):
    def test_abstract_classes_cannot_be_instantiated(self):
        for cls in (Product, Book, Person, DiscountPolicy, Account, Voucher, OrderState):
            with self.subTest(cls=cls.__name__), self.assertRaises(TypeError):
                cls()


class EncapsulationTest(unittest.TestCase):
    def test_setters_reject_invalid_values(self):
        book = physical()
        with self.assertRaises(ValidationError):
            book.price = -1
        with self.assertRaises(ValidationError):
            book.stock = -3
        with self.assertRaises(ValidationError):
            book.title = "   "
        self.assertEqual(book.price, 100_000)

    def test_customer_validates_phone_and_email(self):
        with self.assertRaises(ValidationError):
            Customer(name="A", phone="123")
        with self.assertRaises(ValidationError):
            Customer(name="A", phone="0912345678", email="khong-hop-le")

    def test_take_from_stock_does_not_go_negative(self):
        book = physical(stock=2)
        with self.assertRaises(OutOfStockError):
            book.take_from_stock(3)
        self.assertEqual(book.stock, 2)

    def test_password_is_hashed_and_verified(self):
        encoded = PasswordHasher.hash("bimat123")
        self.assertNotIn("bimat123", encoded)
        self.assertTrue(PasswordHasher.verify("bimat123", encoded))
        self.assertFalse(PasswordHasher.verify("sai-mat-khau", encoded))
        with self.assertRaises(ValidationError):
            PasswordHasher.hash("123")

    def test_cover_image_name_cannot_be_a_path(self):
        with self.assertRaises(ValidationError):
            physical(cover_image="../bi-mat.txt")
        self.assertEqual(physical(cover_image="BK-1-abc.jpg").cover_image, "BK-1-abc.jpg")


def online_order():
    return Order(order_type=OrderType.ONLINE, payment_method="COD", lines=[OrderLine.from_product(physical(), 1)])


def membership_order():
    return Order(order_type=OrderType.MEMBERSHIP, payment_method="CK",
                 lines=[OrderLine.from_product(MembershipPlan(), 1)])


class OrderStateTest(unittest.TestCase):
    """State Pattern: mỗi trạng thái tự quyết định thao tác hợp lệ."""

    def test_book_order_must_ship_before_complete(self):
        order = online_order()
        self.assertEqual(order.available_actions, (OrderAction.SHIP, OrderAction.CANCEL))
        with self.assertRaises(ValidationError):
            order.complete()
        order.ship()
        self.assertEqual(order.status, OrderStatus.SHIPPING)
        self.assertFalse(order.customer_can_cancel)
        self.assertEqual(order.available_actions, (OrderAction.COMPLETE, OrderAction.CANCEL))
        order.complete()
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertEqual(order.available_actions, ())
        with self.assertRaises(ValidationError):
            order.cancel()

    def test_shipping_order_can_be_cancelled(self):
        order = online_order()
        order.ship()
        order.cancel()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_membership_order_completes_without_shipping(self):
        order = membership_order()
        self.assertEqual(order.available_actions, (OrderAction.COMPLETE, OrderAction.CANCEL))
        with self.assertRaises(ValidationError):
            order.ship()
        order.complete()
        self.assertEqual(order.status, OrderStatus.COMPLETED)

    def test_state_survives_round_trip(self):
        order = online_order()
        order.ship()
        self.assertEqual(Order.from_dict(order.to_dict()).status, OrderStatus.SHIPPING)


class VoucherTest(unittest.TestCase):
    TODAY = date(2026, 6, 1)

    def test_percent_and_fixed_vouchers(self):
        percent = PercentVoucher(code="sv10", rate=0.10, min_subtotal=200_000)
        fixed = FixedAmountVoucher(code="GIAM30K", amount=30_000)
        self.assertEqual(percent.code, "SV10")
        self.assertEqual(percent.calculate(100_000, None, 1), 0)
        self.assertEqual(percent.calculate(300_000, None, 1), 30_000)
        self.assertEqual(fixed.calculate(20_000, None, 1), 20_000)  # không giảm quá giá trị đơn

    def test_usability_rules(self):
        voucher = PercentVoucher(code="HE2026", rate=0.1, valid_until="2026-05-31", usage_limit=1)
        with self.assertRaisesRegex(ValidationError, "hết hạn"):
            voucher.check_usable(500_000, self.TODAY)
        voucher = PercentVoucher(code="MOTLAN", rate=0.1, usage_limit=1)
        voucher.use()
        with self.assertRaisesRegex(ValidationError, "hết lượt"):
            voucher.check_usable(500_000, self.TODAY)
        voucher.release()
        voucher.check_usable(500_000, self.TODAY)
        voucher.active = False
        with self.assertRaisesRegex(ValidationError, "ngừng"):
            voucher.check_usable(500_000, self.TODAY)

    def test_invalid_vouchers_are_rejected(self):
        with self.assertRaises(ValidationError):
            PercentVoucher(code="X", rate=0.1)
        with self.assertRaises(ValidationError):
            PercentVoucher(code="QUANHIEU", rate=0.9)
        with self.assertRaises(ValidationError):
            Voucher.create({"kind": "FREESHIP", "code": "ABC", "value": 1})

    def test_round_trip_and_form(self):
        voucher = Voucher.create({"kind": "PERCENT", "code": "sv15", "value": "15", "min_subtotal": "100000"})
        self.assertIsInstance(voucher, PercentVoucher)
        self.assertEqual(voucher.rate, 0.15)
        copy = Voucher.restore(voucher.to_dict())
        self.assertIs(type(copy), PercentVoucher)
        self.assertEqual(copy.to_dict(), voucher.to_dict())


class PolymorphismTest(unittest.TestCase):
    def test_shipping_fee_depends_on_product_type(self):
        self.assertEqual(physical(weight_grams=450).shipping_fee(), 20_000)
        self.assertEqual(physical(weight_grams=620).shipping_fee(), 25_000)
        self.assertEqual(physical(weight_grams=1000).shipping_fee(), 25_000)
        self.assertEqual(physical(weight_grams=1001).shipping_fee(), 30_000)
        self.assertEqual(ebook().shipping_fee(), 0)

    def test_only_physical_books_are_sold_and_restocked(self):
        self.assertTrue(physical().purchasable)
        self.assertFalse(ebook().purchasable)
        with self.assertRaises(ValidationError):
            Cart().add(ebook())
        with self.assertRaises(UnsupportedOperationError):
            ebook().restock(5)

    def test_return_to_stock(self):
        book = physical(stock=1)
        book.return_to_stock(2)
        self.assertEqual(book.stock, 3)
        ebook().return_to_stock(2)  # sách số: không làm gì, không lỗi

    def test_discount_strategies(self):
        vip = VIPCustomer(name="V", phone="0911111111", base_tier=VIPTier.GOLD)
        self.assertEqual(NoDiscount().calculate(500_000, vip, 1), 0)
        self.assertEqual(VIPDiscount().calculate(500_000, vip, 1), 75_000)
        self.assertEqual(VIPDiscount().calculate(500_000, None, 1), 0)
        self.assertEqual(SeasonalPromotion().calculate(249_999, None, 1), 0)
        self.assertEqual(SeasonalPromotion().calculate(300_000, None, 1), 36_000)
        self.assertEqual(BulkOrderDiscount().calculate(400_000, None, 3), 0)
        self.assertEqual(BulkOrderDiscount().calculate(400_000, None, 4), 60_000)

    def test_registry_picks_best_discount(self):
        registry = DiscountRegistry.default()
        gold = VIPCustomer(name="V", phone="0911111111", base_tier=VIPTier.GOLD)
        self.assertEqual(registry.best_for(100_000, None, 1).code, NoDiscount.CODE)
        self.assertEqual(registry.best_for(300_000, None, 1).code, SeasonalPromotion.CODE)
        self.assertEqual(registry.best_for(300_000, None, 4).code, BulkOrderDiscount.CODE)
        self.assertEqual(registry.best_for(300_000, gold, 1).code, VIPDiscount.CODE)

    def test_accounts_know_their_role(self):
        customer_account = CustomerAccount(login="a@b.vn", password_hash="x$1$y$z", customer_id="KH-1")
        admin = AdminAccount(login="admin", password_hash="x$1$y$z")
        self.assertFalse(customer_account.is_admin)
        self.assertTrue(admin.is_admin)
        self.assertEqual(customer_account.home_endpoint, "accounts.profile")
        self.assertEqual(admin.home_endpoint, "admin.dashboard")


class InheritanceTest(unittest.TestCase):
    def test_vip_tier_upgrades_with_spending(self):
        vip = VIPCustomer(name="V", phone="0911111111")
        self.assertEqual(vip.tier, VIPTier.BRONZE)
        vip.record_purchase(3_000_000)
        self.assertEqual(vip.tier, VIPTier.SILVER)
        vip.record_purchase(12_000_000)
        self.assertEqual(vip.tier, VIPTier.PLATINUM)
        self.assertEqual(vip.discount_rate, 0.20)

    def test_vip_earns_double_points(self):
        regular = Customer(name="R", phone="0922222222")
        vip = VIPCustomer(name="V", phone="0933333333")
        self.assertEqual(regular.record_purchase(100_000), 10)
        self.assertEqual(vip.record_purchase(100_000), 20)

    def test_factories_round_trip(self):
        for product in (physical(), ebook()):
            with self.subTest(cls=type(product).__name__):
                copy = ProductFactory.create(product.to_dict())
                self.assertIs(type(copy), type(product))
                self.assertEqual(copy.to_dict(), product.to_dict())
        vip = VIPCustomer(name="V", phone="0911111111", base_tier=VIPTier.GOLD)
        self.assertEqual(CustomerFactory.from_dict(vip.to_dict()).to_dict(), vip.to_dict())
        for account in (CustomerAccount(login="a@b.vn", password_hash="h", customer_id="KH-1"),
                        AdminAccount(login="admin", password_hash="h", display_name="Chủ")):
            with self.subTest(cls=type(account).__name__):
                copy = Account.restore(account.to_dict())
                self.assertIs(type(copy), type(account))
                self.assertEqual(copy.to_dict(), account.to_dict())

    def test_factory_rejects_unknown_format(self):
        with self.assertRaises(ValidationError):
            ProductFactory.create({**BOOK, "format": "VINYL"})


class MembershipTest(unittest.TestCase):
    NOW = datetime(2026, 1, 1, 12, 0, 0)

    def test_renew_extends_from_current_expiry(self):
        membership = EBookMembership()
        membership.renew(days=365, fee=100_000, payment_ref="A", now=self.NOW)
        later = self.NOW + timedelta(days=100)
        membership.renew(days=365, fee=100_000, payment_ref="B", now=later)
        self.assertEqual(membership.expires_at, self.NOW + timedelta(days=730))
        self.assertEqual(membership.total_paid, 200_000)

    def test_expiry_and_revoke(self):
        membership = EBookMembership()
        membership.renew(days=30, fee=0, payment_ref="A", now=self.NOW)
        self.assertTrue(membership.is_valid(self.NOW + timedelta(days=29)))
        self.assertFalse(membership.is_valid(self.NOW + timedelta(days=31)))
        membership.revoke(self.NOW)
        self.assertFalse(membership.is_valid(self.NOW))

    def test_vault_requires_valid_membership(self):
        vault = EBookVault()
        book = ebook()
        customer = Customer(name="A", phone="0912345678")
        with self.assertRaises(AccessDeniedError):
            vault.open_ebook(book, customer, self.NOW)
        with self.assertRaises(AccessDeniedError):
            vault.open_folder(None, self.NOW)
        customer.membership.renew(days=365, fee=100_000, payment_ref="X", now=self.NOW)
        self.assertEqual(vault.open_ebook(book, customer, self.NOW), "https://drive.google.com/x")
        self.assertEqual(vault.open_folder(customer, self.NOW), vault.folder_url)


class AdLedgerTest(unittest.TestCase):
    def test_counts_views_per_day(self):
        ledger = AdLedger()
        day = datetime(2026, 3, 1, 10)
        ledger.record(day)
        ledger.record(day)
        ledger.record(day + timedelta(days=1))
        self.assertEqual(ledger.total_views, 3)
        self.assertEqual(ledger.views_on(day.date()), 2)
        self.assertEqual(AdLedger.from_dict(ledger.to_dict()).total_views, 3)


class CartTest(unittest.TestCase):
    def test_cart_merges_duplicates_and_checks_stock(self):
        book = physical(stock=3)
        cart = Cart()
        cart.add(book, 2)
        cart.add(book, 1)
        self.assertEqual(len(cart), 1)
        self.assertEqual(cart.quantity_of(book.id), 3)
        with self.assertRaises(OutOfStockError):
            cart.add(book, 1)
        self.assertEqual(cart.subtotal(), 300_000)


class AccountPasswordTest(unittest.TestCase):
    def test_change_password_requires_old_password(self):
        account = CustomerAccount(login="a@b.vn", password_hash=PasswordHasher.hash("cu123456"), customer_id="KH-1")
        with self.assertRaises(AuthenticationError):
            account.change_password("sai", "moi123456")
        account.change_password("cu123456", "moi123456")
        self.assertTrue(account.check_password("moi123456"))


if __name__ == "__main__":
    unittest.main()
