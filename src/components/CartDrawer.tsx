import React from 'react';
import { Book } from '../types';
import { formatCurrency, getFormatLabel } from '../utils/formatters';
import {
  X,
  ShoppingCart,
  Trash2,
  Plus,
  Minus,
  ArrowRight,
  ShieldCheck,
  Tag,
} from 'lucide-react';

export interface CustomerCartItem {
  book: Book;
  quantity: number;
}

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  cart: CustomerCartItem[];
  onUpdateQuantity: (bookId: string, delta: number) => void;
  onRemoveItem: (bookId: string) => void;
  onClearCart: () => void;
  onProceedToCheckout: () => void;
  discountCode: string;
  setDiscountCode: (code: string) => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  cart,
  onUpdateQuantity,
  onRemoveItem,
  onClearCart,
  onProceedToCheckout,
  discountCode,
  setDiscountCode,
}) => {
  if (!isOpen) return null;

  const totalQuantity = cart.reduce((sum, it) => sum + it.quantity, 0);
  const subtotal = cart.reduce((sum, it) => sum + it.book.price * it.quantity, 0);

  // Shipping fee calculation:
  // Physical items calculate by weight, digital items 0
  const physicalItems = cart.filter((i) => i.book.format === 'PHYSICAL');
  const shippingFee = physicalItems.length === 0
    ? 0
    : Math.max(...physicalItems.map((i) => i.book.shipping_fee || 20000));

  // Discount calculation
  let discountAmount = 0;
  if (discountCode === 'SEASONAL_12' && subtotal >= 250000) {
    discountAmount = Math.round(subtotal * 0.12);
  } else if (discountCode === 'BULK_15' && totalQuantity >= 4) {
    discountAmount = Math.round(subtotal * 0.15);
  }

  const finalTotal = Math.max(0, subtotal - discountAmount + shippingFee);

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex justify-end">
      <div className="bg-white w-full max-w-md h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-slate-800" />
            <h2 className="text-base font-bold text-slate-900">
              Giỏ Hàng Của Bạn ({totalQuantity})
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Cart Item List */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-3">
          {cart.length === 0 ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400">
                <ShoppingCart className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-slate-800">Giỏ hàng của bạn đang trống</p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Hãy khám phá các tác phẩm đặc sắc trong nhà sách và chọn cho mình cuốn sách yêu thích.
              </p>
              <button
                onClick={onClose}
                className="mt-2 px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
              >
                Khám Phá Sách Ngay
              </button>
            </div>
          ) : (
            cart.map(({ book, quantity }) => (
              <div
                key={book.id}
                className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3 text-xs"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] text-slate-500 font-medium">
                    {getFormatLabel(book.format)}
                  </div>
                  <h4 className="font-bold text-slate-900 truncate mt-0.5">{book.title}</h4>
                  <div className="font-mono text-indigo-700 font-semibold mt-1">
                    {formatCurrency(book.price)}
                  </div>
                </div>

                {/* Stepper */}
                <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-lg p-1 shrink-0">
                  <button
                    onClick={() => onUpdateQuantity(book.id, -1)}
                    className="w-6 h-6 flex items-center justify-center text-slate-600 hover:bg-slate-100 rounded"
                  >
                    <Minus className="w-3 h-3" />
                  </button>
                  <span className="w-6 text-center font-mono font-bold text-slate-900">
                    {quantity}
                  </span>
                  <button
                    onClick={() => onUpdateQuantity(book.id, 1)}
                    className="w-6 h-6 flex items-center justify-center text-slate-600 hover:bg-slate-100 rounded"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                </div>

                {/* Subtotal & Delete */}
                <div className="text-right shrink-0">
                  <div className="font-mono font-bold text-slate-900">
                    {formatCurrency(book.price * quantity)}
                  </div>
                  <button
                    onClick={() => onRemoveItem(book.id)}
                    className="text-slate-400 hover:text-rose-600 p-1 mt-1 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Promo Code & Financial Summary */}
        {cart.length > 0 && (
          <div className="p-4 sm:p-5 border-t border-slate-200 bg-slate-50/50 space-y-4">
            {/* Promo selection */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                <Tag className="w-3.5 h-3.5 text-amber-600" />
                Mã ưu đãi & khuyến mãi
              </label>
              <select
                value={discountCode}
                onChange={(e) => setDiscountCode(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none"
              >
                <option value="NONE">Không áp dụng mã giảm giá</option>
                <option value="SEASONAL_12">Mùa Đọc Sách Tri Thức (-12% cho đơn từ 250k)</option>
                <option value="BULK_15">Mua Nhiều Giá Tốt (-15% khi mua từ 4 cuốn)</option>
              </select>
            </div>

            {/* Price breakdown */}
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-500">
                <span>Tạm tính tiền sách:</span>
                <span className="font-mono tabular-nums text-slate-800">{formatCurrency(subtotal)}</span>
              </div>
              {discountAmount > 0 && (
                <div className="flex justify-between text-emerald-600 font-medium">
                  <span>Khuyến mãi giảm:</span>
                  <span className="font-mono tabular-nums">-{formatCurrency(discountAmount)}</span>
                </div>
              )}
              <div className="flex justify-between text-slate-500">
                <span>Phí giao hàng:</span>
                <span className="font-mono tabular-nums text-slate-800">
                  {shippingFee === 0 ? 'Miễn phí (0 ₫)' : formatCurrency(shippingFee)}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-200 flex justify-between font-bold text-sm text-slate-900">
                <span>Tổng cộng:</span>
                <span className="font-mono tabular-nums text-base text-indigo-700">
                  {formatCurrency(finalTotal)}
                </span>
              </div>
            </div>

            {/* Checkout Action */}
            <button
              onClick={() => {
                onClose();
                onProceedToCheckout();
              }}
              className="w-full py-3 px-4 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-xs"
            >
              <span>Đặt Hàng & Thanh Toán</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
