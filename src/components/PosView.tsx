import React, { useState, useMemo } from 'react';
import { Book, Customer, Order } from '../types';
import { formatCurrency, getFormatLabel, getTierLabel } from '../utils/formatters';
import {
  Search,
  ShoppingCart,
  Trash2,
  Plus,
  Minus,
  CheckCircle,
  User,
  CreditCard,
  QrCode,
  Banknote,
  Receipt,
  Printer,
  Sparkles,
  X,
} from 'lucide-react';

interface CartItem {
  book: Book;
  quantity: number;
}

interface PosViewProps {
  books: Book[];
  customers: Customer[];
  onOrderCreated: (order: Order) => void;
  onNavigateToCustomers: () => void;
}

export const PosView: React.FC<PosViewProps> = ({
  books,
  customers,
  onOrderCreated,
  onNavigateToCustomers,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [cart, setCart] = useState<CartItem[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('');
  const [discountCode, setDiscountCode] = useState<string>('NONE');
  const [paymentMethod, setPaymentMethod] = useState<string>('Tiền mặt');
  const [isProcessing, setIsProcessing] = useState(false);
  const [completedOrder, setCompletedOrder] = useState<Order | null>(null);

  // Selected customer object
  const currentCustomer = useMemo(() => {
    return customers.find((c) => c.id === selectedCustomerId) || null;
  }, [customers, selectedCustomerId]);

  // Categories
  const categories = useMemo(() => {
    return Array.from(new Set(books.map((b) => b.category))).sort();
  }, [books]);

  // Catalog filtered
  const filteredCatalog = useMemo(() => {
    return books.filter((b) => {
      const matchSearch =
        searchQuery === '' ||
        b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.author.toLowerCase().includes(searchQuery.toLowerCase());
      const matchCat = selectedCategory === 'ALL' || b.category === selectedCategory;
      return matchSearch && matchCat;
    });
  }, [books, searchQuery, selectedCategory]);

  // Cart operations
  const addToCart = (book: Book) => {
    if (book.format === 'PHYSICAL' && book.stock <= 0) {
      alert(`Sách "${book.title}" hiện đã hết hàng trong kho.`);
      return;
    }

    setCart((prev) => {
      const existing = prev.find((item) => item.book.id === book.id);
      if (existing) {
        if (book.format === 'PHYSICAL' && existing.quantity >= book.stock) {
          alert(`Chỉ còn ${book.stock} cuốn trong kho.`);
          return prev;
        }
        return prev.map((item) =>
          item.book.id === book.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { book, quantity: 1 }];
    });
  };

  const updateQuantity = (bookId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) => {
          if (item.book.id === bookId) {
            const newQty = item.quantity + delta;
            if (newQty <= 0) return null;
            if (item.book.format === 'PHYSICAL' && newQty > item.book.stock) {
              alert(`Chỉ còn ${item.book.stock} cuốn trong kho.`);
              return item;
            }
            return { ...item, quantity: newQty };
          }
          return item;
        })
        .filter(Boolean) as CartItem[]
    );
  };

  const removeFromCart = (bookId: string) => {
    setCart((prev) => prev.filter((item) => item.book.id !== bookId));
  };

  const clearCart = () => {
    setCart([]);
  };

  // Calculations
  const cartSubtotal = useMemo(() => {
    return cart.reduce((sum, item) => sum + item.book.price * item.quantity, 0);
  }, [cart]);

  const totalItemCount = useMemo(() => {
    return cart.reduce((sum, item) => sum + item.quantity, 0);
  }, [cart]);

  // Shipping: physical items calculate by weight; digital items 0
  const estimatedShipping = useMemo(() => {
    const physicalItems = cart.filter((i) => i.book.format === 'PHYSICAL');
    if (physicalItems.length === 0) return 0;
    return Math.max(...physicalItems.map((i) => i.book.shipping_fee || 20000));
  }, [cart]);

  // Discount calculation
  const estimatedDiscount = useMemo(() => {
    let disc = 0;
    if (discountCode === 'VIP_TIER' || (currentCustomer?.is_vip && discountCode === 'NONE')) {
      if (currentCustomer) {
        disc = cartSubtotal * (currentCustomer.discount_rate || 0.05);
      }
    } else if (discountCode === 'SEASONAL_12') {
      if (cartSubtotal >= 250000) {
        disc = cartSubtotal * 0.12;
      }
    } else if (discountCode === 'BULK_15') {
      if (totalItemCount >= 4) {
        disc = cartSubtotal * 0.15;
      }
    }
    return Math.round(disc);
  }, [discountCode, currentCustomer, cartSubtotal, totalItemCount]);

  const finalTotal = Math.max(0, cartSubtotal - estimatedDiscount + estimatedShipping);

  // Submit checkout
  const handleCheckout = async () => {
    if (cart.length === 0) {
      alert('Vui lòng thêm ít nhất một cuốn sách vào hóa đơn.');
      return;
    }

    setIsProcessing(true);
    try {
      const { api } = await import('../services/api');
      const order = await api.createOrder({
        customer_id: selectedCustomerId || null,
        items: cart.map((it) => ({ id: it.book.id, quantity: it.quantity })),
        discount_code: discountCode,
        payment_method: paymentMethod,
      });

      onOrderCreated(order);
      setCompletedOrder(order);
      setCart([]);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Lỗi trong quá trình thanh toán');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Điểm Bán Hàng & Thu Ngân (POS)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Bán lẻ sách nhanh, tự động tính chiết khấu thành viên, áp dụng khuyến mãi và in hóa đơn thanh toán.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500">Giỏ hàng:</span>
          <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2.5 py-1 rounded-md">
            {totalItemCount} sản phẩm
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left column: Catalog browser (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Search & Filter */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm sách nhanh..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-700 focus:outline-none"
            >
              <option value="ALL">Mọi thể loại ({categories.length})</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Product Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[640px] overflow-y-auto pr-1">
            {filteredCatalog.map((b) => {
              const isPhysical = b.format === 'PHYSICAL';
              const isOut = isPhysical && b.stock <= 0;

              return (
                <div
                  key={b.id}
                  onClick={() => !isOut && addToCart(b)}
                  className={`bg-white border border-slate-200 rounded-xl p-4 flex flex-col justify-between transition-all cursor-pointer ${
                    isOut
                      ? 'opacity-50 cursor-not-allowed bg-slate-50'
                      : 'hover:border-slate-400 hover:shadow-xs'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                      <span className="font-semibold text-slate-700">{getFormatLabel(b.format)}</span>
                      <span>{b.category}</span>
                    </div>
                    <h3 className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug">
                      {b.title}
                    </h3>
                    <div className="text-[11px] text-slate-500 mt-0.5">{b.author}</div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold font-mono tabular-nums text-slate-900">
                        {formatCurrency(b.price)}
                      </span>
                    </div>

                    <div className="text-[11px]">
                      {isPhysical ? (
                        <span
                          className={`font-mono tabular-nums ${
                            b.stock <= 5 ? 'text-amber-600 font-bold' : 'text-slate-500'
                          }`}
                        >
                          Kho: {b.stock}
                        </span>
                      ) : (
                        <span className="text-emerald-600 font-medium">Có sẵn</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right column: Cart & Checkout (5 cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 space-y-5 sticky top-20 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <ShoppingCart className="w-4 h-4 text-slate-700" />
              <h2 className="text-sm font-bold text-slate-900">Hóa Đơn Thu Ngân</h2>
            </div>
            {cart.length > 0 && (
              <button
                onClick={clearCart}
                className="text-xs text-slate-400 hover:text-rose-600 transition-colors"
              >
                Xóa giỏ hàng
              </button>
            )}
          </div>

          {/* Customer Selection */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-500" />
                Khách hàng
              </label>
              <button
                onClick={onNavigateToCustomers}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium"
              >
                + Thêm khách mới
              </button>
            </div>
            <select
              value={selectedCustomerId}
              onChange={(e) => setSelectedCustomerId(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
            >
              <option value="">Khách vãng lai (Giá niêm yết)</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} - {c.phone} {c.is_vip ? `[Hạng ${c.tier} - Giảm ${(c.discount_rate * 100).toFixed(0)}%]` : ''}
                </option>
              ))}
            </select>

            {currentCustomer && (
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1 mt-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">{currentCustomer.name}</span>
                  <span className="text-[11px] font-mono text-slate-500">
                    Điểm tích lũy: <b className="text-slate-900">{currentCustomer.loyalty_points}</b>
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  {getTierLabel(currentCustomer.tier)} · Tổng chi tiêu: {formatCurrency(currentCustomer.total_spent)}
                </div>
              </div>
            )}
          </div>

          {/* Cart item list */}
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {cart.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">
                Chưa có sách nào trong hóa đơn. Click vào sách bên trái để thêm.
              </div>
            ) : (
              cart.map(({ book, quantity }) => (
                <div
                  key={book.id}
                  className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between gap-3 text-xs"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-slate-900 truncate">{book.title}</div>
                    <div className="text-[11px] text-slate-500">
                      {formatCurrency(book.price)} · {getFormatLabel(book.format)}
                    </div>
                  </div>

                  {/* Quantity adjustment */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => updateQuantity(book.id, -1)}
                      className="w-6 h-6 rounded bg-white border border-slate-200 flex items-center justify-center text-slate-600 hover:bg-slate-100"
                    >
                      <Minus className="w-3 h-3" />
                    </button>
                    <span className="w-6 text-center font-mono tabular-nums font-semibold text-slate-900">
                      {quantity}
                    </span>
                    <button
                      onClick={() => updateQuantity(book.id, 1)}
                      className="w-6 h-6 rounded bg-white border border-slate-200 flex items-center justify-center text-slate-600 hover:bg-slate-100"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>

                  <div className="text-right shrink-0 w-20">
                    <div className="font-mono tabular-nums font-bold text-slate-900">
                      {formatCurrency(book.price * quantity)}
                    </div>
                  </div>

                  <button
                    onClick={() => removeFromCart(book.id)}
                    className="text-slate-400 hover:text-rose-600 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Discount Policy */}
          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Chương trình khuyến mãi & chiết khấu
            </label>
            <select
              value={discountCode}
              onChange={(e) => setDiscountCode(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none"
            >
              <option value="NONE">Không áp dụng mã giảm giá riêng</option>
              <option value="VIP_TIER">
                Chiết khấu thành viên VIP (Tự động theo hạng Đồng/Bạc/Vàng/Bạch Kim)
              </option>
              <option value="SEASONAL_12">
                Mùa Đọc Sách Tri Thức (-12% cho hóa đơn từ 250.000đ)
              </option>
              <option value="BULK_15">
                Mua Nhiều Giá Tốt (-15% khi mua từ 4 cuốn trở lên)
              </option>
            </select>
          </div>

          {/* Payment Method */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">Phương thức thanh toán</label>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setPaymentMethod('Tiền mặt')}
                className={`py-2 px-1 text-center rounded-lg border transition-colors flex flex-col items-center gap-1 ${
                  paymentMethod === 'Tiền mặt'
                    ? 'border-slate-900 bg-slate-50 text-slate-900 font-semibold'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <Banknote className="w-4 h-4 text-emerald-600" />
                <span>Tiền mặt</span>
              </button>
              <button
                type="button"
                onClick={() => setPaymentMethod('Chuyển khoản QR')}
                className={`py-2 px-1 text-center rounded-lg border transition-colors flex flex-col items-center gap-1 ${
                  paymentMethod === 'Chuyển khoản QR'
                    ? 'border-slate-900 bg-slate-50 text-slate-900 font-semibold'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <QrCode className="w-4 h-4 text-blue-600" />
                <span>Mã QR</span>
              </button>
              <button
                type="button"
                onClick={() => setPaymentMethod('Thẻ tín dụng')}
                className={`py-2 px-1 text-center rounded-lg border transition-colors flex flex-col items-center gap-1 ${
                  paymentMethod === 'Thẻ tín dụng'
                    ? 'border-slate-900 bg-slate-50 text-slate-900 font-semibold'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <CreditCard className="w-4 h-4 text-purple-600" />
                <span>Thẻ POS</span>
              </button>
            </div>
          </div>

          {/* Summary Financial breakdown */}
          <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
            <div className="flex items-center justify-between text-slate-500">
              <span>Tạm tính tiền sách:</span>
              <span className="font-mono tabular-nums text-slate-800">
                {formatCurrency(cartSubtotal)}
              </span>
            </div>

            {estimatedDiscount > 0 && (
              <div className="flex items-center justify-between text-emerald-600 font-medium">
                <span>Chiết khấu khuyến mãi:</span>
                <span className="font-mono tabular-nums">-{formatCurrency(estimatedDiscount)}</span>
              </div>
            )}

            <div className="flex items-center justify-between text-slate-500">
              <span>Phí giao hàng:</span>
              <span className="font-mono tabular-nums text-slate-800">
                {estimatedShipping === 0 ? '0 ₫' : formatCurrency(estimatedShipping)}
              </span>
            </div>

            <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-sm font-bold text-slate-900">
              <span>Tổng thanh toán:</span>
              <span className="text-lg font-mono tabular-nums text-indigo-700">
                {formatCurrency(finalTotal)}
              </span>
            </div>
          </div>

          {/* Checkout CTA */}
          <button
            onClick={handleCheckout}
            disabled={cart.length === 0 || isProcessing}
            className="w-full py-3 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50 transition-colors shadow-xs"
          >
            {isProcessing ? 'Đang xuất hóa đơn...' : `Thanh Toán & Xuất Hóa Đơn (${formatCurrency(finalTotal)})`}
          </button>
        </div>
      </div>

      {/* COMPLETED ORDER RECEIPT MODAL */}
      {completedOrder && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-900">Thanh Toán Thành Công</h3>
              </div>
              <button
                onClick={() => setCompletedOrder(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Printable Receipt Card */}
            <div className="mt-4 p-5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-3 font-mono">
              <div className="text-center pb-2 border-b border-dashed border-slate-300">
                <div className="font-bold text-sm text-slate-900 tracking-wider">NHÀ SÁCH TRÍ TRI</div>
                <div className="text-[11px] text-slate-500">Hóa Đơn Bán Lẻ</div>
                <div className="text-[11px] text-slate-500 mt-1">Mã HĐ: {completedOrder.id}</div>
                <div className="text-[11px] text-slate-500">{completedOrder.created_at}</div>
              </div>

              {completedOrder.customer && (
                <div className="text-[11px] text-slate-700 py-1 border-b border-slate-200">
                  <div>Khách hàng: {completedOrder.customer.name}</div>
                  <div>SĐT: {completedOrder.customer.phone} · {getTierLabel(completedOrder.customer.tier)}</div>
                </div>
              )}

              <div className="space-y-1.5 py-1 border-b border-dashed border-slate-300">
                {completedOrder.items.map((it, idx) => (
                  <div key={idx} className="flex justify-between">
                    <span className="truncate max-w-[200px]">
                      {it.quantity}x {it.title}
                    </span>
                    <span className="tabular-nums">{formatCurrency(it.subtotal)}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between text-slate-500">
                  <span>Tạm tính:</span>
                  <span className="tabular-nums">{formatCurrency(completedOrder.subtotal)}</span>
                </div>
                {completedOrder.discount_amount > 0 && (
                  <div className="flex justify-between text-emerald-700">
                    <span>Chiết khấu ({completedOrder.discount_policy.description}):</span>
                    <span className="tabular-nums">-{formatCurrency(completedOrder.discount_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-slate-500">
                  <span>Phí giao hàng:</span>
                  <span className="tabular-nums">
                    {completedOrder.shipping_fee === 0 ? '0 ₫' : formatCurrency(completedOrder.shipping_fee)}
                  </span>
                </div>
                <div className="flex justify-between font-bold text-slate-900 text-xs pt-1 border-t border-slate-300">
                  <span>TỔNG TIỀN:</span>
                  <span className="tabular-nums text-sm text-indigo-700">
                    {formatCurrency(completedOrder.final_total)}
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 pt-1">
                  Phương thức: {completedOrder.payment_method} · Trạng thái: {completedOrder.status}
                </div>
              </div>
            </div>

            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                onClick={() => window.print()}
                className="px-4 py-2 text-xs font-medium text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-50 flex items-center gap-1.5"
              >
                <Printer className="w-3.5 h-3.5" />
                In Hóa Đơn
              </button>
              <button
                onClick={() => setCompletedOrder(null)}
                className="px-5 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800"
              >
                Hoàn Tất & Tiếp Tục Bán
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
