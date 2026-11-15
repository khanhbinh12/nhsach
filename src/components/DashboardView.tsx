import React from 'react';
import { Statistics } from '../types';
import { formatCurrency, getFormatLabel } from '../utils/formatters';
import {
  TrendingUp,
  Package,
  ShoppingCart,
  Users,
  AlertTriangle,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import { AdminTab } from './Header';

interface DashboardViewProps {
  stats: Statistics | null;
  loading: boolean;
  onNavigate: (tab: AdminTab) => void;
  onRestockClick: (bookId: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  stats,
  loading,
  onNavigate,
  onRestockClick,
}) => {
  if (loading || !stats) {
    return (
      <div className="py-16 flex justify-center items-center">
        <div className="text-sm text-slate-500 font-mono animate-pulse">
          Đang tải dữ liệu vận hành nhà sách...
        </div>
      </div>
    );
  }

  const categoryEntries = Object.entries(stats.category_revenue || {});
  const totalCatRevenue = categoryEntries.reduce((sum, [, val]) => sum + val, 0) || 1;

  return (
    <div className="space-y-8">
      {/* Editorial Intro Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
              Bảng Điều Khiển Nhà Sách
            </span>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight" style={{ textWrap: 'balance' }}>
              Tổng Quan Tình Hình Kinh Doanh
            </h1>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Theo dõi biến động doanh thu, xuất nhập tồn kho thực tế, tình trạng đơn hàng thu ngân và phân hạng khách hàng thân thiết trong thời gian thực.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigate('pos')}
              className="px-4 py-2.5 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shadow-xs"
            >
              Mở Thu Ngân Bán Hàng
            </button>
            <button
              onClick={() => onNavigate('inventory')}
              className="px-4 py-2.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors rounded-lg whitespace-nowrap"
            >
              Quản Lý Kho Sách
            </button>
          </div>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Doanh Thu Thuần</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {formatCurrency(stats.total_revenue)}
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
            <span>Tích lũy từ</span>
            <span className="font-semibold text-slate-700 font-mono">{stats.total_orders}</span>
            <span>đơn hoàn tất</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Đơn Hàng Đã Xử Lý</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <ShoppingCart className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {stats.total_orders}
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
            <span>Đã ghi nhận hóa đơn bán lẻ</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Tổng Đầu Sách & Kho</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {stats.total_books_types}{' '}
            <span className="text-sm font-normal text-slate-500">tựa sách</span>
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
            <span className="font-semibold text-slate-700 font-mono">{stats.total_physical_stock}</span>
            <span>cuốn sách in có sẵn</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Khách Hàng Đăng Ký</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {stats.total_customers}
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
            <span>Bao gồm khách VIP và khách thành viên</span>
          </div>
        </div>
      </div>

      {/* Low Stock Warning Section */}
      {stats.low_stock_items && stats.low_stock_items.length > 0 && (
        <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-amber-900">
                Cảnh Báo Tồn Kho Sắp Hết ({stats.low_stock_items.length} cuốn còn dưới 5 sản phẩm)
              </h3>
            </div>
            <button
              onClick={() => onNavigate('inventory')}
              className="text-xs font-semibold text-amber-800 hover:text-amber-950 flex items-center gap-1"
            >
              <span>Xem chi tiết kho sách</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {stats.low_stock_items.map((b) => (
              <div
                key={b.id}
                className="bg-white border border-amber-200/80 rounded-lg p-3 flex items-center justify-between gap-3 shadow-2xs"
              >
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-900 truncate">{b.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {b.author} · Vị trí: {b.shelf_location || 'Kho'}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="font-mono tabular-nums font-bold text-xs text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-100">
                    Còn {b.stock}
                  </span>
                  <button
                    onClick={() => onRestockClick(b.id)}
                    className="text-xs px-2.5 py-1 bg-amber-600 text-white font-medium rounded hover:bg-amber-700 transition-colors"
                  >
                    Nhập Thêm
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid: Top Sellers & Category Revenue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Top Sellers Table */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Top Sách Bán Chạy</h2>
              <p className="text-xs text-slate-500 mt-0.5">Xếp hạng theo số lượng bản in & ấn bản đã bán</p>
            </div>
            <button
              onClick={() => onNavigate('inventory')}
              className="text-xs font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1"
            >
              Xem danh mục <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-medium">
                  <th className="py-2.5 pr-3 font-normal">TỰA SÁCH</th>
                  <th className="py-2.5 px-3 font-normal">ĐỊNH DẠNG</th>
                  <th className="py-2.5 px-3 text-right font-normal">ĐÃ BÁN</th>
                  <th className="py-2.5 pl-3 text-right font-normal">DOANH THU</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {stats.top_sellers && stats.top_sellers.length > 0 ? (
                  stats.top_sellers.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 pr-3">
                        <div className="font-semibold text-slate-900 truncate max-w-xs">
                          {item.title}
                        </div>
                        <div className="text-slate-500 text-[11px] mt-0.5">{item.category}</div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-slate-600 font-medium">
                          {getFormatLabel(item.format)}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-semibold text-slate-900">
                        {item.total_sold} cuốn
                      </td>
                      <td className="py-3 pl-3 text-right font-mono tabular-nums text-slate-700">
                        {formatCurrency(item.revenue)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-slate-400">
                      Chưa có dữ liệu bán lẻ.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Category Revenue Breakdown */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-bold text-slate-900">Cơ Cấu Doanh Thu Theo Thể Loại</h2>
          <p className="text-xs text-slate-500 mt-0.5 mb-4">Tỷ trọng doanh thu theo từng nhóm sách</p>

          <div className="space-y-4">
            {categoryEntries.length > 0 ? (
              categoryEntries.map(([cat, rev]) => {
                const percent = Math.round((rev / totalCatRevenue) * 100);
                return (
                  <div key={cat} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-800">{cat}</span>
                      <span className="font-mono tabular-nums text-slate-600">
                        {formatCurrency(rev)} ({percent}%)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-slate-900 rounded-full transition-all duration-300"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-8 text-center text-xs text-slate-400">
                Chưa có dữ liệu phân bổ doanh thu.
              </div>
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Trạng thái kết nối máy chủ</span>
            <span className="text-emerald-700 font-medium">Hoạt động bình thường</span>
          </div>
        </div>
      </div>
    </div>
  );
};
