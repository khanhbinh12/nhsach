import React, { useState, useMemo } from 'react';
import { Book, BookFormat } from '../types';
import { formatCurrency, getFormatLabel } from '../utils/formatters';
import {
  Search,
  BookOpen,
  Headphones,
  FileText,
  ShoppingCart,
  Eye,
  Check,
  Truck,
  Sparkles,
  ShieldCheck,
  ChevronRight,
} from 'lucide-react';

interface StorefrontViewProps {
  books: Book[];
  categories: string[];
  loading: boolean;
  onAddToCart: (book: Book, quantity: number) => void;
  onSelectBook: (book: Book) => void;
  onOpenCart: () => void;
  cartCount: number;
}

export const StorefrontView: React.FC<StorefrontViewProps> = ({
  books,
  categories,
  loading,
  onAddToCart,
  onSelectBook,
  onOpenCart,
  cartCount,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [addedBookId, setAddedBookId] = useState<string | null>(null);

  const filteredBooks = useMemo(() => {
    return books.filter((b) => {
      const matchSearch =
        searchQuery === '' ||
        b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.author.toLowerCase().includes(searchQuery.toLowerCase());
      const matchFormat = selectedFormat === 'ALL' || b.format === selectedFormat;
      const matchCategory = selectedCategory === 'ALL' || b.category === selectedCategory;
      return matchSearch && matchFormat && matchCategory;
    });
  }, [books, searchQuery, selectedFormat, selectedCategory]);

  const handleQuickAdd = (e: React.MouseEvent, book: Book) => {
    e.stopPropagation();
    onAddToCart(book, 1);
    setAddedBookId(book.id);
    setTimeout(() => setAddedBookId(null), 1500);
  };

  return (
    <div className="space-y-10">
      {/* Editorial Storefront Hero */}
      <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 rounded-2xl p-8 sm:p-12 text-white relative overflow-hidden shadow-lg border border-slate-800">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-amber-300 text-xs font-semibold backdrop-blur-xs">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Không Gian Tri Thức & Ấn Bản Tuyển Chọn</span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-tight" style={{ textWrap: 'balance' }}>
            Khám phá thế giới qua từng trang sách
          </h1>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-xl">
            Tuyển tập sách in truyền thống chất lượng cao, sách điện tử tải ngay lập tức và sách nói truyền cảm với giọng đọc phòng thu chuẩn mực.
          </p>

          {/* Search bar inside Hero */}
          <div className="pt-2 max-w-lg">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm kiếm tác phẩm, tên tác giả, thể loại..."
                className="w-full pl-10 pr-4 py-3 text-xs sm:text-sm bg-white/10 backdrop-blur-md border border-white/20 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:bg-white/20 transition-all"
              />
            </div>
          </div>
        </div>

        {/* Decorative background elements */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-400 via-indigo-500 to-transparent pointer-events-none" />
      </section>

      {/* Value Proposition Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-3 px-4 bg-white border border-slate-200 rounded-xl text-xs text-slate-600 shadow-2xs">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-900">100% Chính Hãng</div>
            <div className="text-[11px] text-slate-500">Bản quyền từ các NXB uy tín</div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-900">E-Book & Sách Nói</div>
            <div className="text-[11px] text-slate-500">Tải & nghe thử tức thì 0đ phí ship</div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <Truck className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-900">Giao Hàng Tận Nơi</div>
            <div className="text-[11px] text-slate-500">Đóng gói cẩn thận chống sốc</div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-900">Tích Lũy Điểm VIP</div>
            <div className="text-[11px] text-slate-500">Ưu đãi thành viên giảm tới 20%</div>
          </div>
        </div>
      </div>

      {/* Filter and Category navigation */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Format tabs */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0 overflow-x-auto">
          <button
            onClick={() => setSelectedFormat('ALL')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
              selectedFormat === 'ALL'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Tất Cả ({books.length})
          </button>
          <button
            onClick={() => setSelectedFormat('PHYSICAL')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              selectedFormat === 'PHYSICAL'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-600" />
            <span>Sách In Giấy</span>
          </button>
          <button
            onClick={() => setSelectedFormat('EBOOK')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              selectedFormat === 'EBOOK'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-emerald-600" />
            <span>E-Book</span>
          </button>
          <button
            onClick={() => setSelectedFormat('AUDIOBOOK')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              selectedFormat === 'AUDIOBOOK'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Headphones className="w-3.5 h-3.5 text-purple-600" />
            <span>Sách Nói</span>
          </button>
        </div>

        {/* Category dropdown */}
        <div className="flex items-center gap-3">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full md:w-auto px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none"
          >
            <option value="ALL">Mọi danh mục sách ({categories.length})</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Catalog Books Grid (3-4 columns responsive) */}
      {loading ? (
        <div className="py-20 text-center text-xs font-mono text-slate-400">
          Đang nạp danh mục sách...
        </div>
      ) : filteredBooks.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <BookOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">Không tìm thấy tựa sách phù hợp</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Hãy thử tìm bằng từ khóa khác hoặc bỏ chọn bộ lọc thể loại.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filteredBooks.map((book) => {
            const isPhysical = book.format === 'PHYSICAL';
            const isEBook = book.format === 'EBOOK';
            const isAudio = book.format === 'AUDIOBOOK';
            const isOut = isPhysical && book.stock <= 0;
            const isJustAdded = addedBookId === book.id;

            return (
              <div
                key={book.id}
                onClick={() => onSelectBook(book)}
                className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:border-slate-300 transition-all duration-200 flex flex-col justify-between group shadow-2xs hover:shadow-md cursor-pointer"
              >
                <div>
                  {/* Book Card Cover Header */}
                  <div className="aspect-[4/3] bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 p-5 flex flex-col justify-between text-white relative overflow-hidden">
                    {/* Spine illusion line */}
                    <div className="absolute left-0 top-0 bottom-0 w-3 bg-gradient-to-r from-black/50 via-black/20 to-transparent" />

                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-amber-400 font-semibold uppercase tracking-wider">
                        {getFormatLabel(book.format)}
                      </span>
                      <span className="text-slate-400 text-[10px]">{book.publish_year}</span>
                    </div>

                    <div className="my-auto py-2">
                      <h3 className="font-bold text-sm text-white line-clamp-2 leading-snug group-hover:text-amber-300 transition-colors">
                        {book.title}
                      </h3>
                      <div className="text-[11px] text-slate-300 mt-1 truncate">{book.author}</div>
                    </div>

                    <div className="text-[10px] text-slate-400 truncate">
                      {book.publisher}
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="p-4 space-y-2">
                    <div className="text-[11px] text-slate-500 font-medium truncate">
                      {book.category}
                    </div>

                    <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                      {book.description || 'Tác phẩm tuyển chọn đặc sắc phát hành chính hãng.'}
                    </p>
                  </div>
                </div>

                {/* Footer Price & Buy Button */}
                <div className="p-4 pt-0">
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Giá bìa niêm yết</span>
                      <span className="text-sm font-bold font-mono tabular-nums text-slate-900">
                        {formatCurrency(book.price)}
                      </span>
                    </div>

                    <button
                      onClick={(e) => handleQuickAdd(e, book)}
                      disabled={isOut}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                        isJustAdded
                          ? 'bg-emerald-600 text-white'
                          : isOut
                          ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                          : 'bg-slate-900 text-white hover:bg-slate-800'
                      }`}
                    >
                      {isJustAdded ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>Đã thêm</span>
                        </>
                      ) : isOut ? (
                        <span>Hết hàng</span>
                      ) : (
                        <>
                          <ShoppingCart className="w-3.5 h-3.5" />
                          <span>Mua sách</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
