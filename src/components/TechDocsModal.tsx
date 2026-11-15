import React, { useState, useEffect } from 'react';
import { OOPArchitecture } from '../types';
import { api } from '../services/api';
import {
  Terminal,
  Play,
  Copy,
  Check,
  Layers,
  Shield,
  GitBranch,
  Sparkles,
  FileCode,
  X,
} from 'lucide-react';

interface TechDocsModalProps {
  isOpen: boolean;
  onClose: () => void;
  architecture: OOPArchitecture | null;
  onRefreshAllData: () => void;
}

const PRESET_SCRIPTS = [
  {
    name: '1. Kiểm tra tính Đa hình',
    description: 'Gọi calculate_shipping_fee() đa hình cho từng loại sách',
    code: `# ĐA HÌNH (Polymorphism) trong Python:
# Cùng gọi calculate_shipping_fee() nhưng PhysicalBook tính theo trọng lượng,
# trong khi EBook và AudioBook miễn phí vận chuyển (0đ)

print("--- KIỂM TRA TÍNH ĐA HÌNH (POLYMORPHISM) ---")
for book in bookstore.inventory.get_all():
    fmt = book.get_format().value
    fee = book.calculate_shipping_fee()
    print(f"[{fmt:<10}] {book.title[:35]:<35} | Giá: {book.price:>9,.0f}đ | Ship: {fee:>7,.0f}đ")
`,
  },
  {
    name: '2. Kiểm tra tính Đóng gói',
    description: 'Kiểm tra thuộc tính private _price và setter bảo vệ giá âm',
    code: `# ĐÓNG GÓI (Encapsulation) & XÁC THỰC:
book = bookstore.inventory.get_all()[0]
print(f"Sách: '{book.title}'")
print(f"Giá hiện tại: {book.price:,.0f}đ | Tồn kho: {book.stock} cuốn")

try:
    print("\\n[Test] Thử gán giá âm: book.price = -50000")
    book.price = -50000
except ValueError as e:
    print(f"==> SETTER BẢO VỆ THÀNH CÔNG: {e}")
`,
  },
  {
    name: '3. Strategy Pattern Giảm Giá',
    description: 'Áp dụng các chính sách chiết khấu khác nhau linh hoạt',
    code: `# STRATEGY PATTERN:
subtotal = 500000.0
vip_cust = list(bookstore.customers.values())[0]

print(f"Khách: {vip_cust.name} ({vip_cust.get_tier().value} - Giảm {vip_cust.get_discount_rate()*100:.0f}%)")
for code, policy in bookstore.discount_policies.items():
    discount = policy.calculate_discount(subtotal, vip_cust, item_count=5)
    print(f"Mã: {code:<12} | {policy.get_description():<45} => Giảm: {discount:>8,.0f}đ")
`,
  },
];

export const TechDocsModal: React.FC<TechDocsModalProps> = ({
  isOpen,
  onClose,
  architecture,
  onRefreshAllData,
}) => {
  const [activeTab, setActiveTab] = useState<'pillars' | 'console' | 'source'>('pillars');
  const [pythonCode, setPythonCode] = useState<string>(PRESET_SCRIPTS[0].code);
  const [consoleOutput, setConsoleOutput] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [sourceCode, setSourceCode] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen && !sourceCode) {
      api.getSourceCode().then(setSourceCode).catch(() => {});
    }
  }, [isOpen, sourceCode]);

  if (!isOpen) return null;

  const handleRunCode = async () => {
    setIsRunning(true);
    setConsoleOutput('Đang gửi lệnh tới Python 3.10 backend...');
    try {
      const res = await api.executePython(pythonCode);
      setConsoleOutput(res.output);
      onRefreshAllData();
    } catch (err: unknown) {
      setConsoleOutput(`Lỗi thực thi: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleCopySource = () => {
    navigator.clipboard.writeText(sourceCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full p-6 max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                Hồ Sơ Kỹ Thuật & Cấu Trúc Backend (Python OOP)
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Toàn bộ nghiệp vụ quản lý nhà sách bên dưới được vận hành bởi máy chủ Python theo 4 nguyên lý hướng đối tượng
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Tab switchers */}
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg text-xs">
              <button
                onClick={() => setActiveTab('pillars')}
                className={`px-3 py-1.5 font-medium rounded-md transition-colors ${
                  activeTab === 'pillars' ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-600'
                }`}
              >
                4 Trụ Cột OOP
              </button>
              <button
                onClick={() => setActiveTab('console')}
                className={`px-3 py-1.5 font-medium rounded-md transition-colors ${
                  activeTab === 'console' ? 'bg-white text-indigo-700 shadow-2xs font-bold' : 'text-slate-600'
                }`}
              >
                Chạy Thử Python
              </button>
              <button
                onClick={() => setActiveTab('source')}
                className={`px-3 py-1.5 font-medium rounded-md transition-colors ${
                  activeTab === 'source' ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-600'
                }`}
              >
                Mã Nguồn
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* TAB 1: 4 Pillars */}
          {activeTab === 'pillars' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-indigo-600 font-bold text-xs">
                    <Layers className="w-4 h-4" />
                    <span>1. Tính Trừu Tượng (Abstraction)</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Sử dụng <code>abc.ABC</code> định nghĩa giao diện chung cho các đối tượng trong nhà sách: <code>Item</code>, <code>DiscountPolicy</code>, <code>Person</code>.
                  </p>
                  <div className="font-mono text-[11px] bg-white p-2.5 rounded border border-slate-200 text-slate-700 space-y-0.5">
                    <div>class Item(ABC):</div>
                    <div className="pl-3 text-slate-500">@abstractmethod def calculate_shipping_fee(self)</div>
                    <div className="pl-3 text-slate-500">@abstractmethod def to_dict(self)</div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-emerald-600 font-bold text-xs">
                    <Shield className="w-4 h-4" />
                    <span>2. Tính Đóng Gói (Encapsulation)</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Thuộc tính nhạy cảm như <code>_price</code>, <code>_stock</code>, <code>_loyalty_points</code> được bảo vệ bằng <code>@property</code> và setter kiểm tra điều kiện.
                  </p>
                  <div className="font-mono text-[11px] bg-white p-2.5 rounded border border-slate-200 text-slate-700 space-y-0.5">
                    <div>@price.setter def price(self, val):</div>
                    <div className="pl-3 text-slate-500">if val &lt; 0: raise ValueError("Giá không thể âm")</div>
                    <div className="pl-3 text-slate-500">self._price = val</div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-blue-600 font-bold text-xs">
                    <GitBranch className="w-4 h-4" />
                    <span>3. Tính Kế Thừa (Inheritance)</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Tái sử dụng mã nguồn và mở rộng phân loại:
                  </p>
                  <div className="font-mono text-[11px] bg-white p-2.5 rounded border border-slate-200 text-slate-700 space-y-1">
                    <div>Item ➔ Book ➔ PhysicalBook (kệ, trọng lượng)</div>
                    <div className="pl-8">➔ EBook (link tải, dung lượng file)</div>
                    <div className="pl-8">➔ AudioBook (giọng đọc, thời lượng)</div>
                    <div>Person ➔ Customer ➔ VIPCustomer</div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-amber-600 font-bold text-xs">
                    <Sparkles className="w-4 h-4" />
                    <span>4. Tính Đa Hình (Polymorphism)</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Thực thi phương thức linh hoạt dựa trên bản chất của từng đối tượng:
                  </p>
                  <div className="font-mono text-[11px] bg-white p-2.5 rounded border border-slate-200 text-slate-700 space-y-0.5">
                    <div>PhysicalBook.calculate_shipping_fee() ➔ theo gam</div>
                    <div>EBook.calculate_shipping_fee() ➔ 0 ₫</div>
                    <div>DiscountPolicy.calculate_discount() ➔ Strategy Pattern</div>
                  </div>
                </div>
              </div>

              {architecture && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <span className="text-xs font-bold text-slate-900 block mb-2">
                    Danh Sách Lớp Đối Tượng (Python Classes Catalog)
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono">
                    {architecture.classes.map((c, i) => (
                      <div key={i} className="p-2 bg-white rounded border border-slate-200">
                        <div className="font-bold text-indigo-700">{c.name}</div>
                        <div className="text-[11px] text-slate-500 font-sans">{c.type}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Python Console */}
          {activeTab === 'console' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {PRESET_SCRIPTS.map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => setPythonCode(preset.code)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors"
                  >
                    {preset.name}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900 rounded-xl p-3 flex flex-col justify-between">
                  <div className="text-xs text-slate-400 font-mono pb-2 border-b border-slate-800">
                    Mã Python thử nghiệm (biến: bookstore, inventory, customers)
                  </div>
                  <textarea
                    rows={10}
                    value={pythonCode}
                    onChange={(e) => setPythonCode(e.target.value)}
                    className="w-full bg-transparent text-emerald-400 font-mono text-xs focus:outline-none resize-none pt-2 leading-relaxed"
                  />
                  <div className="pt-2 border-t border-slate-800 text-right">
                    <button
                      onClick={handleRunCode}
                      disabled={isRunning}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-500"
                    >
                      <Play className="w-3 h-3" />
                      <span>{isRunning ? 'Đang chạy...' : 'Chạy thử'}</span>
                    </button>
                  </div>
                </div>

                <div className="bg-slate-950 rounded-xl p-3 font-mono text-xs text-slate-200 overflow-y-auto max-h-72 whitespace-pre-wrap leading-relaxed">
                  <div className="text-slate-400 pb-2 border-b border-slate-800">
                    Kết quả thực thi (stdout)
                  </div>
                  <div className="pt-2">
                    {consoleOutput || <span className="text-slate-600 italic">Bấm "Chạy thử" để xem output...</span>}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Source code */}
          {activeTab === 'source' && (
            <div className="bg-slate-900 rounded-xl p-4 text-xs font-mono text-slate-300 space-y-2">
              <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                <span>backend/bookstore_oop.py</span>
                <button
                  onClick={handleCopySource}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded flex items-center gap-1"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Đã sao chép' : 'Sao chép'}</span>
                </button>
              </div>
              <pre className="max-h-96 overflow-y-auto p-2 bg-black/30 rounded leading-relaxed">
                {sourceCode || 'Đang tải mã nguồn Python...'}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
          >
            Đóng Hồ Sơ Kỹ Thuật
          </button>
        </div>
      </div>
    </div>
  );
};
