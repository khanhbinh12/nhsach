import React, { useState } from 'react';
import { Customer, VIPTier } from '../types';
import { formatCurrency, getTierLabel } from '../utils/formatters';
import { Search, Plus, User, Award, Phone, Mail, X } from 'lucide-react';

interface CustomersViewProps {
  customers: Customer[];
  loading: boolean;
  onCreateCustomer: (data: {
    name: string;
    phone: string;
    email: string;
    is_vip: boolean;
    tier?: string;
  }) => Promise<void>;
}

export const CustomersView: React.FC<CustomersViewProps> = ({
  customers,
  loading,
  onCreateCustomer,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'ALL' | 'VIP' | 'REGULAR'>('ALL');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [isVip, setIsVip] = useState(false);
  const [tier, setTier] = useState<VIPTier>('BRONZE');

  const filteredCustomers = customers.filter((c) => {
    const matchSearch =
      searchQuery === '' ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.phone.includes(searchQuery) ||
      c.email.toLowerCase().includes(searchQuery.toLowerCase());

    const matchType =
      filterType === 'ALL' ||
      (filterType === 'VIP' && c.is_vip) ||
      (filterType === 'REGULAR' && !c.is_vip);

    return matchSearch && matchType;
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !phone.trim()) {
      alert('Vui lòng nhập tên và số điện thoại');
      return;
    }

    setIsSubmitting(true);
    try {
      await onCreateCustomer({
        name: name.trim(),
        phone: phone.trim(),
        email: email.trim(),
        is_vip: isVip,
        tier: isVip ? tier : 'STANDARD',
      });
      setIsModalOpen(false);
      setName('');
      setPhone('');
      setEmail('');
      setIsVip(false);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Lỗi khi tạo khách hàng');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Quản Lý Khách Hàng & Thành Viên
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Theo dõi danh sách khách hàng, điểm tích lũy thành viên, phân hạng thẻ VIP và lịch sử mua sắm.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors shrink-0 shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Khách Hàng Mới</span>
        </button>
      </div>

      {/* Filter & Search */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên khách, số điện thoại, email..."
            className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>

        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0">
          <button
            onClick={() => setFilterType('ALL')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              filterType === 'ALL'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Tất Cả ({customers.length})
          </button>
          <button
            onClick={() => setFilterType('VIP')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              filterType === 'VIP'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Hội Viên VIP ({customers.filter((c) => c.is_vip).length})
          </button>
          <button
            onClick={() => setFilterType('REGULAR')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              filterType === 'REGULAR'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Thường ({customers.filter((c) => !c.is_vip).length})
          </button>
        </div>
      </div>

      {/* Customers Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50 text-slate-400 font-medium">
                <th className="py-3 px-4 font-normal">HỌ VÀ TÊN</th>
                <th className="py-3 px-4 font-normal">LIÊN HỆ</th>
                <th className="py-3 px-4 font-normal">HẠNG THÀNH VIÊN</th>
                <th className="py-3 px-4 text-right font-normal">ĐIỂM TÍCH LŨY</th>
                <th className="py-3 px-4 text-right font-normal">TỔNG CHI TIÊU</th>
                <th className="py-3 px-4 text-right font-normal">ƯU ĐÃI GIẢM</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 font-mono">
                    Đang nạp danh sách khách hàng...
                  </td>
                </tr>
              ) : filteredCustomers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    Không tìm thấy khách hàng nào.
                  </td>
                </tr>
              ) : (
                filteredCustomers.map((cust) => (
                  <tr key={cust.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>{cust.name}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        Mã: {cust.id}
                      </div>
                    </td>

                    <td className="py-3 px-4 space-y-0.5">
                      <div className="text-slate-700 flex items-center gap-1 font-mono">
                        <Phone className="w-3 h-3 text-slate-400" />
                        <span>{cust.phone}</span>
                      </div>
                      {cust.email && (
                        <div className="text-slate-400 flex items-center gap-1 text-[11px]">
                          <Mail className="w-3 h-3 text-slate-400" />
                          <span className="truncate max-w-xs">{cust.email}</span>
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      {cust.is_vip ? (
                        <div className="inline-flex items-center gap-1 text-indigo-700 font-semibold bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                          <Award className="w-3.5 h-3.5" />
                          <span>VIP {cust.tier}</span>
                        </div>
                      ) : (
                        <span className="text-slate-600 font-medium">Thành viên thường</span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums font-semibold text-slate-900">
                      {cust.loyalty_points} điểm
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums font-medium text-slate-700">
                      {formatCurrency(cust.total_spent)}
                    </td>

                    <td className="py-3 px-4 text-right font-mono tabular-nums font-bold text-indigo-600">
                      {(cust.discount_rate * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Add Customer */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Thêm Khách Hàng Mới</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Họ và tên <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="VD: Lê Thị Hồng"
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
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="VD: 0912345678"
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="VD: hong.le@example.com"
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                />
              </div>

              {/* VIP Checkbox */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-900 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isVip}
                    onChange={(e) => setIsVip(e.target.checked)}
                    className="rounded text-slate-900 focus:ring-slate-900"
                  />
                  <span>Đăng ký thẻ Khách hàng VIP</span>
                </label>

                {isVip && (
                  <div className="pt-2 border-t border-slate-200">
                    <label className="block text-xs text-slate-600 mb-1">Hạng thẻ ban đầu</label>
                    <select
                      value={tier}
                      onChange={(e) => setTier(e.target.value as VIPTier)}
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded text-slate-800"
                    >
                      <option value="BRONZE">Thẻ Đồng (Giảm 5%)</option>
                      <option value="SILVER">Thẻ Bạc (Giảm 10%)</option>
                      <option value="GOLD">Thẻ Vàng (Giảm 15%)</option>
                      <option value="PLATINUM">Thẻ Bạch Kim (Giảm 20%)</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50"
                >
                  {isSubmitting ? 'Đang tạo...' : 'Lưu Khách Hàng'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
