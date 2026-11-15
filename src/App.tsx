import React, { useState, useEffect, useCallback } from 'react';
import { Header, AppMode, AdminTab } from './components/Header';
import { StorefrontView } from './components/StorefrontView';
import { DashboardView } from './components/DashboardView';
import { InventoryView } from './components/InventoryView';
import { PosView } from './components/PosView';
import { CustomersView } from './components/CustomersView';
import { OrdersView } from './components/OrdersView';
import { BookDetailModal } from './components/BookDetailModal';
import { CartDrawer, CustomerCartItem } from './components/CartDrawer';
import { CheckoutModal } from './components/CheckoutModal';
import { TechDocsModal } from './components/TechDocsModal';
import { Book, Customer, Order, Statistics, OOPArchitecture } from './types';
import { api } from './services/api';

export default function App() {
  const [appMode, setAppMode] = useState<AppMode>('storefront');
  const [adminTab, setAdminTab] = useState<AdminTab>('dashboard');

  // Server data
  const [books, setBooks] = useState<Book[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<Statistics | null>(null);
  const [architecture, setArchitecture] = useState<OOPArchitecture | null>(null);
  const [loading, setLoading] = useState(true);
  const [isResetting, setIsResetting] = useState(false);
  const [preselectedRestockId, setPreselectedRestockId] = useState<string | null>(null);

  // Storefront customer cart & modals
  const [customerCart, setCustomerCart] = useState<CustomerCartItem[]>([]);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [selectedBookForDetail, setSelectedBookForDetail] = useState<Book | null>(null);
  const [storeDiscountCode, setStoreDiscountCode] = useState('NONE');
  const [isTechDocsOpen, setIsTechDocsOpen] = useState(false);

  // Load all data from Python backend
  const loadData = useCallback(async () => {
    try {
      const [booksData, catsData, custsData, ordersData, statsData, archData] = await Promise.all([
        api.getBooks(),
        api.getCategories(),
        api.getCustomers(),
        api.getOrders(),
        api.getStats(),
        api.getOOPArchitecture(),
      ]);

      setBooks(booksData);
      setCategories(catsData);
      setCustomers(custsData);
      setOrders(ordersData);
      setStats(statsData);
      setArchitecture(archData);
    } catch (err) {
      console.error('[App] Lỗi nạp dữ liệu từ Python:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Customer Cart operations
  const handleAddToCart = (book: Book, quantity: number = 1) => {
    if (book.format === 'PHYSICAL' && book.stock <= 0) {
      alert(`Sách "${book.title}" hiện đã hết hàng trong kho.`);
      return;
    }

    setCustomerCart((prev) => {
      const existing = prev.find((it) => it.book.id === book.id);
      if (existing) {
        const nextQty = existing.quantity + quantity;
        if (book.format === 'PHYSICAL' && nextQty > book.stock) {
          alert(`Chỉ còn ${book.stock} cuốn trong kho.`);
          return prev;
        }
        return prev.map((it) =>
          it.book.id === book.id ? { ...it, quantity: nextQty } : it
        );
      }
      return [...prev, { book, quantity }];
    });
  };

  const handleUpdateCartQuantity = (bookId: string, delta: number) => {
    setCustomerCart((prev) =>
      prev
        .map((it) => {
          if (it.book.id === bookId) {
            const nextQty = it.quantity + delta;
            if (nextQty <= 0) return null;
            if (it.book.format === 'PHYSICAL' && nextQty > it.book.stock) {
              alert(`Chỉ còn ${it.book.stock} cuốn trong kho.`);
              return it;
            }
            return { ...it, quantity: nextQty };
          }
          return it;
        })
        .filter(Boolean) as CustomerCartItem[]
    );
  };

  const handleRemoveCartItem = (bookId: string) => {
    setCustomerCart((prev) => prev.filter((it) => it.book.id !== bookId));
  };

  const handleClearCart = () => {
    setCustomerCart([]);
  };

  const handleBuyNow = (book: Book) => {
    handleAddToCart(book, 1);
    setIsCheckoutOpen(true);
  };

  // Online order confirmed callback
  const handleOrderSuccess = (newOrder: Order) => {
    setOrders((prev) => [newOrder, ...prev]);
    loadData();
  };

  // Admin Book CRUD operations
  const handleCreateBook = async (bookData: Partial<Book>) => {
    await api.createBook(bookData);
    await loadData();
  };

  const handleUpdateBook = async (id: string, bookData: Partial<Book>) => {
    await api.updateBook(id, bookData);
    await loadData();
  };

  const handleDeleteBook = async (id: string) => {
    await api.deleteBook(id);
    await loadData();
  };

  const handleRestockBook = async (id: string, quantity: number) => {
    await api.restockBook(id, quantity);
    await loadData();
  };

  // Admin Customer operations
  const handleCreateCustomer = async (data: {
    name: string;
    phone: string;
    email: string;
    is_vip: boolean;
    tier?: string;
  }) => {
    await api.createCustomer(data);
    await loadData();
  };

  // Reset demo data
  const handleResetData = async () => {
    if (confirm('Bạn có muốn đặt lại toàn bộ kho sách và đơn hàng về trạng thái mẫu ban đầu?')) {
      setIsResetting(true);
      try {
        await api.resetData();
        await loadData();
        setCustomerCart([]);
      } catch (err) {
        alert(err instanceof Error ? err.message : 'Lỗi đặt lại dữ liệu');
      } finally {
        setIsResetting(false);
      }
    }
  };

  // Shortcut from dashboard to inventory restock
  const handleRestockClickFromDashboard = (bookId: string) => {
    setPreselectedRestockId(bookId);
    setAdminTab('inventory');
  };

  const totalCartCount = customerCart.reduce((sum, it) => sum + it.quantity, 0);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 selection:bg-slate-900 selection:text-white">
      {/* Top Header */}
      <Header
        appMode={appMode}
        setAppMode={setAppMode}
        adminTab={adminTab}
        setAdminTab={setAdminTab}
        onResetData={handleResetData}
        isResetting={isResetting}
        onOpenTechDocs={() => setIsTechDocsOpen(true)}
        cartCount={totalCartCount}
        onOpenCart={() => setIsCartOpen(true)}
      />

      {/* Main Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* 1. STOREFRONT MODE (Khách hàng xem & mua sách online) */}
        {appMode === 'storefront' && (
          <StorefrontView
            books={books}
            categories={categories}
            loading={loading}
            onAddToCart={handleAddToCart}
            onSelectBook={(book) => setSelectedBookForDetail(book)}
            onOpenCart={() => setIsCartOpen(true)}
            cartCount={totalCartCount}
          />
        )}

        {/* 2. ADMIN & MANAGEMENT MODE (Quản lý nhà sách, POS, tồn kho, khách hàng) */}
        {appMode === 'admin' && (
          <>
            {adminTab === 'dashboard' && (
              <DashboardView
                stats={stats}
                loading={loading}
                onNavigate={(tab) => setAdminTab(tab as AdminTab)}
                onRestockClick={handleRestockClickFromDashboard}
              />
            )}

            {adminTab === 'inventory' && (
              <InventoryView
                books={books}
                categories={categories}
                loading={loading}
                onRefresh={loadData}
                onCreateBook={handleCreateBook}
                onUpdateBook={handleUpdateBook}
                onDeleteBook={handleDeleteBook}
                onRestockBook={handleRestockBook}
                preselectedRestockId={preselectedRestockId}
                onClearPreselectedRestock={() => setPreselectedRestockId(null)}
              />
            )}

            {adminTab === 'pos' && (
              <PosView
                books={books}
                customers={customers}
                onOrderCreated={handleOrderSuccess}
                onNavigateToCustomers={() => setAdminTab('customers')}
              />
            )}

            {adminTab === 'customers' && (
              <CustomersView
                customers={customers}
                loading={loading}
                onCreateCustomer={handleCreateCustomer}
              />
            )}

            {adminTab === 'orders' && (
              <OrdersView orders={orders} loading={loading} />
            )}
          </>
        )}
      </main>

      {/* Book Detail & Reading/Audio Sample Modal */}
      <BookDetailModal
        book={selectedBookForDetail}
        onClose={() => setSelectedBookForDetail(null)}
        onAddToCart={handleAddToCart}
        onBuyNow={handleBuyNow}
      />

      {/* Slide-over Customer Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        cart={customerCart}
        onUpdateQuantity={handleUpdateCartQuantity}
        onRemoveItem={handleRemoveCartItem}
        onClearCart={handleClearCart}
        onProceedToCheckout={() => setIsCheckoutOpen(true)}
        discountCode={storeDiscountCode}
        setDiscountCode={setStoreDiscountCode}
      />

      {/* Online Customer Checkout Modal */}
      <CheckoutModal
        isOpen={isCheckoutOpen}
        onClose={() => setIsCheckoutOpen(false)}
        cart={customerCart}
        discountCode={storeDiscountCode}
        onOrderSuccess={handleOrderSuccess}
        onClearCart={handleClearCart}
      />

      {/* Technical Architecture Modal */}
      <TechDocsModal
        isOpen={isTechDocsOpen}
        onClose={() => setIsTechDocsOpen(false)}
        architecture={architecture}
        onRefreshAllData={loadData}
      />

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-8 mt-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900">Nhà Sách Trí Tri</span>
              <span aria-hidden="true">·</span>
              <span>Mua Sách Trực Tuyến & Quản Trị Nhà Sách Toàn Diện</span>
            </div>
            <div className="flex items-center gap-4 text-slate-600">
              <button
                onClick={() => setAppMode(appMode === 'storefront' ? 'admin' : 'storefront')}
                className="font-medium hover:text-slate-900 transition-colors"
              >
                {appMode === 'storefront' ? 'Chuyển sang Bàn Quản Trị' : 'Chuyển sang Cửa Hàng Bán Sách'}
              </button>
              <span aria-hidden="true">·</span>
              <button
                onClick={() => setIsTechDocsOpen(true)}
                className="hover:text-indigo-600 transition-colors"
              >
                Hồ sơ kỹ thuật backend (Python OOP)
              </button>
            </div>
          </div>
          <div className="text-[11px] text-slate-400 text-center sm:text-left">
            Hotline đặt sách & hỗ trợ độc giả: 1900 6868 · Giao hàng toàn quốc · Cam kết 100% sách có bản quyền
          </div>
        </div>
      </footer>
    </div>
  );
}
