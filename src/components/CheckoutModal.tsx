import React, { useState } from 'react';
import { Book, Order } from '../types';
import { CustomerCartItem } from './CartDrawer';
import { formatCurrency, getFormatLabel } from '../utils/formatters';
import { api } from '../services/api';
import {
  X,
  CheckCircle,
  Truck,
  CreditCard,
  QrCode,
  Banknote,
  Download,
  Headphones,
  ShoppingBag,
  ArrowRight,
  ShieldCheck,
  FileText,
} from 'lucide-react';

interface CheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  cart: CustomerCartItem[];
  discountCode: string;
  onOrderSuccess: (order: Order) => void;
  onClearCart: () => void;
}

export const CheckoutModal: React.FC<CheckoutModalProps> = ({
  isOpen,
  onClose,
  cart,
  discountCode,
  onOrderSuccess,
  onClearCart,
}) => {
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [shippingAddress, setShippingAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('Thanh toán khi nhận hàng (COD)');
  const [customerNotes, setCustomerNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmedOrder, setConfirmedOrder] = useState<Order | null>(null);

  if (!isOpen) return null;

  const hasPhysicalBooks = cart.some((it) => it.book.format === 'PHYSICAL');
  const hasEBooks = cart.some((it) => it.book.format === 'EBOOK');
  const hasAudioBooks = cart.some((it) => it.book.format === 'AUDIOBOOK');

  const subtotal = cart.reduce((sum, it) => sum + it.book.price * it.quantity, 0);
  const totalQuantity = cart.reduce((sum, it) => sum + it.quantity, 0);

  const physicalItems = cart.filter((i) => i.book.format === 'PHYSICAL');
  const shippingFee = physicalItems.length === 0
    ? 0
    : Math.max(...physicalItems.map((i) => i.book.shipping_fee || 20000));

  let discountAmount = 0;
  if (discountCode === 'SEASONAL_12' && subtotal >= 250000) {
    discountAmount = Math.round(subtotal * 0.12);
  } else if (discountCode === 'BULK_15' && totalQuantity >= 4) {
    discountAmount = Math.round(subtotal * 0.15);
  }

  const finalTotal = Math.max(0, subtotal - discountAmount + shippingFee);

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerName.trim() || !customerPhone.trim()) {
      alert('Vui lòng nhập họ tên và số điện thoại người nhận.');
      return;
    }

    if (hasPhysicalBooks && !shippingAddress.trim()) {
      alert('Vui lòng nhập địa chỉ nhận sách in.');
      return;
    }

    setIsSubmitting(true);
    try {
      const order = await api.createOrder({
        customer_info: {
          name: customerName.trim(),
          phone: customerPhone.trim(),
          email: customerEmail.trim() || undefined,
        },
        shipping_address: shippingAddress.trim(),
        order_type: 'ONLINE',
        items: cart.map((it) => ({ id: it.book.id, quantity: it.quantity })),
        discount_code: discountCode,
        payment_method: paymentMethod,
      });

      onOrderSuccess(order);
      setConfirmedOrder(order);
      onClearCart();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Lỗi khi đặt hàng');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 max-h-[92vh] overflow-y-auto relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {!confirmedOrder ? (
          <div>
            {/* Header */}
            <div className="pb-4 border-b border-slate-200">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                Thanh Toán Đơn Hàng Online
              </span>
              <h2 className="text-xl font-bold text-slate-900 mt-1">
                Thông Tin Giao Hàng & Thanh Toán
              </h2>
            </div>

            <form onSubmit={handleSubmitOrder} className="mt-5 space-y-5">
              {/* Customer information */}
              <div className="space-y-3">
                <span className="text-xs font-bold text-slate-900 block">
                  1. Thông tin người nhận
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Họ và tên <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      placeholder="VD: Nguyễn Văn Nam"
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Số điện thoại <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="tel"
                      required
                      value={customerPhone}
                      onChange={(e) => setCustomerPhone(e.target.value)}
                      placeholder="VD: 0987654321"
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Email nhận hóa đơn & file E-Book {hasEBooks && <span className="text-rose-500">*</span>}
                    </label>
                    <input
                      type="email"
                      required={hasEBooks}
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                      placeholder="VD: nam.nguyen@example.com (Dùng để nhận link tải sách điện tử)"
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                    />
                  </div>

                  {hasPhysicalBooks && (
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Địa chỉ nhận hàng (Sách in) <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        required={hasPhysicalBooks}
                        value={shippingAddress}
                        onChange={(e) => setShippingAddress(e.target.value)}
                        placeholder="Số nhà, đường, phường/xã, quận/huyện, tỉnh/thành phố..."
                        className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Payment methods */}
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <span className="text-xs font-bold text-slate-900 block">
                  2. Phương thức thanh toán
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('Thanh toán khi nhận hàng (COD)')}
                    className={`p-3 rounded-xl border text-left text-xs transition-colors flex flex-col justify-between gap-2 ${
                      paymentMethod.includes('COD')
                        ? 'border-slate-900 bg-slate-50 font-semibold text-slate-900 shadow-2xs'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-bold">
                      <Truck className="w-4 h-4 text-emerald-600" />
                      <span>COD</span>
                    </div>
                    <span className="text-[11px] text-slate-500">Thanh toán tiền mặt khi nhận sách</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod('Chuyển khoản QR ngân hàng (VietQR)')}
                    className={`p-3 rounded-xl border text-left text-xs transition-colors flex flex-col justify-between gap-2 ${
                      paymentMethod.includes('QR')
                        ? 'border-slate-900 bg-slate-50 font-semibold text-slate-900 shadow-2xs'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-bold">
                      <QrCode className="w-4 h-4 text-blue-600" />
                      <span>Quét mã VietQR</span>
                    </div>
                    <span className="text-[11px] text-slate-500">Chuyển khoản tức thì qua ứng dụng Mobile Banking</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod('Thẻ ngân hàng / Thẻ quốc tế')}
                    className={`p-3 rounded-xl border text-left text-xs transition-colors flex flex-col justify-between gap-2 ${
                      paymentMethod.includes('Thẻ')
                        ? 'border-slate-900 bg-slate-50 font-semibold text-slate-900 shadow-2xs'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-bold">
                      <CreditCard className="w-4 h-4 text-purple-600" />
                      <span>Thẻ ATM / Visa</span>
                    </div>
                    <span className="text-[11px] text-slate-500">Cổng thanh toán thẻ nội địa & quốc tế</span>
                  </button>
                </div>
              </div>

              {/* Order review summary */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                <span className="font-bold text-slate-900 block mb-1">
                  Đơn hàng ({totalQuantity} cuốn sách)
                </span>
                <div className="space-y-1 max-h-32 overflow-y-auto pr-1">
                  {cart.map((it, idx) => (
                    <div key={idx} className="flex justify-between items-center text-slate-600">
                      <span className="truncate max-w-xs">
                        {it.quantity}x {it.book.title} ({getFormatLabel(it.book.format)})
                      </span>
                      <span className="font-mono tabular-nums font-medium text-slate-800">
                        {formatCurrency(it.book.price * it.quantity)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-slate-200 space-y-1">
                  <div className="flex justify-between text-slate-500">
                    <span>Tạm tính tiền sách:</span>
                    <span className="font-mono tabular-nums text-slate-800">{formatCurrency(subtotal)}</span>
                  </div>
                  {discountAmount > 0 && (
                    <div className="flex justify-between text-emerald-600 font-medium">
                      <span>Khuyến mãi áp dụng:</span>
                      <span className="font-mono tabular-nums">-{formatCurrency(discountAmount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-slate-500">
                    <span>Phí vận chuyển:</span>
                    <span className="font-mono tabular-nums text-slate-800">
                      {shippingFee === 0 ? 'Miễn phí (0 ₫)' : formatCurrency(shippingFee)}
                    </span>
                  </div>
                  <div className="pt-1.5 border-t border-slate-200 flex justify-between font-bold text-sm text-slate-900">
                    <span>Tổng số tiền thanh toán:</span>
                    <span className="font-mono tabular-nums text-base text-indigo-700">
                      {formatCurrency(finalTotal)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
                >
                  Quay lại giỏ hàng
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-2.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-xl transition-colors disabled:opacity-50 shadow-xs"
                >
                  {isSubmitting ? 'Đang tạo đơn hàng...' : `Xác Nhận Đặt Hàng (${formatCurrency(finalTotal)})`}
                </button>
              </div>
            </form>
          </div>
        ) : (
          /* ORDER CONFIRMATION SUCCESS SCREEN */
          <div className="py-6 text-center space-y-5">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-xs">
              <CheckCircle className="w-8 h-8" />
            </div>

            <div>
              <h2 className="text-xl font-bold text-slate-900">
                Đặt Hàng Thành Công!
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Cảm ơn bạn đã mua sách tại Nhà Sách Trí Tri. Mã đơn hàng của bạn là{' '}
                <span className="font-mono font-bold text-slate-900">{confirmedOrder.id}</span>
              </p>
            </div>

            {/* Product fulfillment cards */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-left text-xs space-y-3">
              <span className="font-bold text-slate-900 block">
                Thông tin sản phẩm & nhận sách
              </span>

              {confirmedOrder.items.map((it, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-white border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <span className="text-[11px] text-slate-500 font-medium">
                      {getFormatLabel(it.format)}
                    </span>
                    <h4 className="font-bold text-slate-900 truncate">{it.title}</h4>
                    <span className="font-mono text-slate-600">{it.quantity} cuốn · {formatCurrency(it.subtotal)}</span>
                  </div>

                  <div className="shrink-0">
                    {it.format === 'EBOOK' && (
                      <button
                        onClick={() => alert(`Đang tải file ${it.title} về máy...`)}
                        className="px-3 py-1.5 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 transition-colors flex items-center gap-1.5"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Tải File E-Book</span>
                      </button>
                    )}

                    {it.format === 'AUDIOBOOK' && (
                      <button
                        onClick={() => alert(`Mở trình phát nghe sách nói ${it.title}...`)}
                        className="px-3 py-1.5 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-1.5"
                      >
                        <Headphones className="w-3.5 h-3.5" />
                        <span>Nghe Ngay</span>
                      </button>
                    )}

                    {it.format === 'PHYSICAL' && (
                      <span className="text-slate-600 flex items-center gap-1">
                        <Truck className="w-3.5 h-3.5 text-blue-600" />
                        <span>Đang đóng gói giao tận nhà</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 flex items-center justify-center gap-3">
              <button
                onClick={() => {
                  setConfirmedOrder(null);
                  onClose();
                }}
                className="px-6 py-2.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-xl transition-colors shadow-xs"
              >
                Tiếp Tục Khám Phá Sách
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
