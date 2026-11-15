import React, { useState } from 'react';
import { Order } from '../types';
import { formatCurrency, getFormatLabel, getTierLabel } from '../utils/formatters';
import { Search, Receipt, Printer, Eye, X } from 'lucide-react';

interface OrdersViewProps {
  orders: Order[];
  loading: boolean;
}

export const OrdersView: React.FC<OrdersViewProps> = ({ orders, loading }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  const filteredOrders = orders.filter((o) => {
    const q = searchQuery.toLowerCase();
    const matchId = o.id.toLowerCase().includes(q);
    const matchCustomer = o.customer?.name.toLowerCase().includes(q) || false;
    const matchPhone = o.customer?.phone.includes(q) || false;
    return matchId || matchCustomer || matchPhone || q === '';
  });

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Lịch Sử Đơn Hàng & Hóa Đơn
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Theo dõi toàn bộ lịch sử các giao dịch bán lẻ, chi tiết từng đầu sách và in lại hóa đơn.
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between gap-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo mã hóa đơn (HD-...), tên khách hàng hoặc SĐT..."
            className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50 text-slate-400 font-medium">
                <th className="py-3 px-4 font-normal">MÃ ĐƠN HÀNG</th>
                <th className="py-3 px-4 font-normal">THỜI GIAN</th>
                <th className="py-3 px-4 font-normal">KHÁCH HÀNG</th>
                <th className="py-3 px-4 text-center font-normal">SỐ CUỐN</th>
                <th className="py-3 px-4 text-right font-normal">TẠM TÍNH</th>
                <th className="py-3 px-4 text-right font-normal">CHIẾT KHẤU</th>
                <th className="py-3 px-4 text-right font-normal">PHÍ GIAO HÀNG</th>
                <th className="py-3 px-4 text-right font-normal">TỔNG CỘNG</th>
                <th className="py-3 px-4 text-center font-normal">THAO TÁC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400 font-mono">
                    Đang nạp dữ liệu hóa đơn...
                  </td>
                </tr>
              ) : filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    Không tìm thấy hóa đơn nào phù hợp.
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {order.id}
                    </td>

                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                      {order.created_at}
                    </td>

                    <td className="py-3 px-4">
                      {order.customer ? (
                        <div>
                          <div className="font-semibold text-slate-900">{order.customer.name}</div>
                          <div className="text-[11px] text-slate-500">{order.customer.phone}</div>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Khách vãng lai</span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-center font-mono tabular-nums text-slate-700">
                      {order.total_quantity}
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-600">
                      {formatCurrency(order.subtotal)}
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums text-emerald-600">
                      {order.discount_amount > 0 ? `-${formatCurrency(order.discount_amount)}` : '0 ₫'}
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-600">
                      {order.shipping_fee === 0 ? '0 ₫' : formatCurrency(order.shipping_fee)}
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums font-bold text-slate-900">
                      {formatCurrency(order.final_total)}
                    </td>

                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => setSelectedOrder(order)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Xem</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invoice Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Chi Tiết Hóa Đơn</h3>
              </div>
              <button
                onClick={() => setSelectedOrder(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 p-5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-3 font-mono">
              <div className="text-center pb-2 border-b border-dashed border-slate-300">
                <div className="font-bold text-sm text-slate-900 tracking-wider">NHÀ SÁCH TRÍ TRI</div>
                <div className="text-[11px] text-slate-500">Mã hóa đơn: {selectedOrder.id}</div>
                <div className="text-[11px] text-slate-500">{selectedOrder.created_at}</div>
              </div>

              {selectedOrder.customer && (
                <div className="text-[11px] text-slate-700 py-1 border-b border-slate-200">
                  <div>Khách hàng: {selectedOrder.customer.name}</div>
                  <div>SĐT: {selectedOrder.customer.phone} · {getTierLabel(selectedOrder.customer.tier)}</div>
                </div>
              )}

              <div className="space-y-1.5 py-1 border-b border-dashed border-slate-300">
                {selectedOrder.items.map((it, idx) => (
                  <div key={idx} className="flex justify-between items-start">
                    <div>
                      <div className="font-semibold text-slate-900">
                        {it.quantity}x {it.title}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {getFormatLabel(it.format)} · Đơn giá: {formatCurrency(it.unit_price)}
                      </div>
                    </div>
                    <span className="tabular-nums font-bold text-slate-800">
                      {formatCurrency(it.subtotal)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between text-slate-500">
                  <span>Tạm tính tiền sách:</span>
                  <span className="tabular-nums">{formatCurrency(selectedOrder.subtotal)}</span>
                </div>
                {selectedOrder.discount_amount > 0 && (
                  <div className="flex justify-between text-emerald-700">
                    <span>Chiết khấu ({selectedOrder.discount_policy.description}):</span>
                    <span className="tabular-nums">-{formatCurrency(selectedOrder.discount_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-slate-500">
                  <span>Phí giao hàng:</span>
                  <span className="tabular-nums">
                    {selectedOrder.shipping_fee === 0 ? '0 ₫' : formatCurrency(selectedOrder.shipping_fee)}
                  </span>
                </div>
                <div className="flex justify-between font-bold text-slate-900 text-xs pt-1 border-t border-slate-300">
                  <span>TỔNG THANH TOÁN:</span>
                  <span className="tabular-nums text-sm text-indigo-700">
                    {formatCurrency(selectedOrder.final_total)}
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 pt-1">
                  Phương thức: {selectedOrder.payment_method} · Trạng thái: {selectedOrder.status}
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
                onClick={() => setSelectedOrder(null)}
                className="px-5 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
