import React, { useState } from 'react';
import { Book, BookFormat } from '../types';
import { formatCurrency, getFormatLabel } from '../utils/formatters';
import {
  Search,
  Plus,
  PackagePlus,
  Edit2,
  Trash2,
  BookOpen,
  Headphones,
  FileText,
  MapPin,
  Scale,
  Clock,
  Mic,
  AlertCircle,
  X,
} from 'lucide-react';

interface InventoryViewProps {
  books: Book[];
  categories: string[];
  loading: boolean;
  onRefresh: () => void;
  onCreateBook: (data: Partial<Book>) => Promise<void>;
  onUpdateBook: (id: string, data: Partial<Book>) => Promise<void>;
  onDeleteBook: (id: string) => Promise<void>;
  onRestockBook: (id: string, quantity: number) => Promise<void>;
  preselectedRestockId?: string | null;
  onClearPreselectedRestock?: () => void;
}

export const InventoryView: React.FC<InventoryViewProps> = ({
  books,
  categories,
  loading,
  onCreateBook,
  onUpdateBook,
  onDeleteBook,
  onRestockBook,
  preselectedRestockId,
  onClearPreselectedRestock,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingBook, setEditingBook] = useState<Book | null>(null);
  const [restockingBook, setRestockingBook] = useState<Book | null>(() => {
    if (preselectedRestockId) {
      return books.find((b) => b.id === preselectedRestockId) || null;
    }
    return null;
  });
  const [restockAmount, setRestockAmount] = useState<number>(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Form state
  const [formFormat, setFormFormat] = useState<BookFormat>('PHYSICAL');
  const [formTitle, setFormTitle] = useState('');
  const [formAuthor, setFormAuthor] = useState('');
  const [formCategory, setFormCategory] = useState('Công nghệ & Lập trình');
  const [formPrice, setFormPrice] = useState<number>(150000);
  const [formStock, setFormStock] = useState<number>(20);
  const [formPublisher, setFormPublisher] = useState('NXB Trẻ');
  const [formYear, setFormYear] = useState<number>(2024);
  const [formIsbn, setFormIsbn] = useState('');
  const [formDescription, setFormDescription] = useState('');

  // PhysicalBook fields
  const [formWeight, setFormWeight] = useState<number>(450);
  const [formShelf, setFormShelf] = useState('Kệ A-01');
  const [formCover, setFormCover] = useState('Bìa mềm');

  // EBook fields
  const [formFileSize, setFormFileSize] = useState<number>(14.2);
  const [formFileFormat, setFormFileFormat] = useState('PDF');
  const [formDownloadLink, setFormDownloadLink] = useState('');

  // AudioBook fields
  const [formDuration, setFormDuration] = useState<number>(360);
  const [formNarrator, setFormNarrator] = useState('NSƯT Hà Phương');

  // Filter books
  const filteredBooks = books.filter((b) => {
    const matchesSearch =
      searchQuery === '' ||
      b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.isbn.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesFormat = selectedFormat === 'ALL' || b.format === selectedFormat;
    const matchesCategory = selectedCategory === 'ALL' || b.category === selectedCategory;

    return matchesSearch && matchesFormat && matchesCategory;
  });

  const resetForm = () => {
    setFormTitle('');
    setFormAuthor('');
    setFormCategory('Công nghệ & Lập trình');
    setFormPrice(150000);
    setFormStock(20);
    setFormPublisher('NXB Trẻ');
    setFormYear(2024);
    setFormIsbn('');
    setFormDescription('');
    setFormWeight(450);
    setFormShelf('Kệ A-01');
    setFormCover('Bìa mềm');
    setFormFileSize(14.2);
    setFormFileFormat('PDF');
    setFormDownloadLink('');
    setFormDuration(360);
    setFormNarrator('NSƯT Hà Phương');
    setErrorMsg('');
  };

  const handleOpenAdd = () => {
    resetForm();
    setFormFormat('PHYSICAL');
    setIsAddModalOpen(true);
  };

  const handleOpenEdit = (b: Book) => {
    setEditingBook(b);
    setFormFormat(b.format);
    setFormTitle(b.title);
    setFormAuthor(b.author);
    setFormCategory(b.category);
    setFormPrice(b.price);
    setFormStock(b.stock);
    setFormPublisher(b.publisher);
    setFormYear(b.publish_year);
    setFormIsbn(b.isbn);
    setFormDescription(b.description || '');

    if (b.format === 'PHYSICAL') {
      setFormWeight(b.weight_grams || 450);
      setFormShelf(b.shelf_location || 'Kệ A-01');
      setFormCover(b.cover_type || 'Bìa mềm');
    } else if (b.format === 'EBOOK') {
      setFormFileSize(b.file_size_mb || 10);
      setFormFileFormat(b.file_format || 'PDF');
      setFormDownloadLink(b.download_link || '');
    } else if (b.format === 'AUDIOBOOK') {
      setFormDuration(b.duration_minutes || 300);
      setFormNarrator(b.narrator || '');
    }
  };

  const handleSubmitBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formAuthor.trim()) {
      setErrorMsg('Vui lòng nhập tên sách và tác giả.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const payload: Partial<Book> = {
        title: formTitle.trim(),
        author: formAuthor.trim(),
        category: formCategory,
        price: formPrice,
        publisher: formPublisher,
        publish_year: formYear,
        isbn: formIsbn.trim() || `978-604-${Math.floor(Math.random() * 900000 + 100000)}`,
        description: formDescription.trim(),
        format: formFormat,
      };

      if (formFormat === 'PHYSICAL') {
        payload.stock = formStock;
        payload.weight_grams = formWeight;
        payload.shelf_location = formShelf;
        payload.cover_type = formCover;
      } else if (formFormat === 'EBOOK') {
        payload.file_size_mb = formFileSize;
        payload.file_format = formFileFormat;
        payload.download_link = formDownloadLink;
      } else if (formFormat === 'AUDIOBOOK') {
        payload.duration_minutes = formDuration;
        payload.narrator = formNarrator;
      }

      if (editingBook) {
        await onUpdateBook(editingBook.id, payload);
        setEditingBook(null);
      } else {
        await onCreateBook(payload);
        setIsAddModalOpen(false);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Đã có lỗi xảy ra');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRestockSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!restockingBook || restockAmount <= 0) return;

    setIsSubmitting(true);
    try {
      await onRestockBook(restockingBook.id, restockAmount);
      setRestockingBook(null);
      if (onClearPreselectedRestock) onClearPreselectedRestock();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Lỗi nhập kho');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Action bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Quản Lý Danh Mục & Kho Sách
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Quản lý tồn kho sách in, ấn bản điện tử (E-Book) và sách nói (Audio Book). Cập nhật vị trí kệ, giá bìa và nhập hàng.
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors shrink-0 shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Sách Mới</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row items-stretch md:items-center gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên sách, tác giả, mã ISBN..."
            className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 text-slate-900"
          />
        </div>

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
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
              selectedFormat === 'PHYSICAL'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Sách In
          </button>
          <button
            onClick={() => setSelectedFormat('EBOOK')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
              selectedFormat === 'EBOOK'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            E-Book
          </button>
          <button
            onClick={() => setSelectedFormat('AUDIOBOOK')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
              selectedFormat === 'AUDIOBOOK'
                ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Sách Nói
          </button>
        </div>

        {/* Category selector */}
        <div className="shrink-0">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full md:w-auto px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-900"
          >
            <option value="ALL">Mọi thể loại ({categories.length})</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Books Table / Grid */}
      {loading ? (
        <div className="py-16 text-center text-xs font-mono text-slate-400">
          Đang truy vấn danh mục sách...
        </div>
      ) : filteredBooks.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <BookOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">Không tìm thấy sách phù hợp</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Thử thay đổi từ khóa tìm kiếm, bộ lọc thể loại hoặc thêm một cuốn sách mới vào hệ thống.
          </p>
          <button
            onClick={handleOpenAdd}
            className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
          >
            Thêm Sách Mới
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredBooks.map((book) => {
            const isPhysical = book.format === 'PHYSICAL';
            const isEBook = book.format === 'EBOOK';
            const isAudio = book.format === 'AUDIOBOOK';
            const isLowStock = isPhysical && book.stock <= 5;

            return (
              <div
                key={book.id}
                className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between hover:border-slate-300 transition-colors shadow-2xs relative"
              >
                <div>
                  {/* Top metadata strip */}
                  <div className="flex items-center justify-between gap-2 text-xs text-slate-500 mb-2">
                    <span className="font-semibold text-slate-700 flex items-center gap-1">
                      {isPhysical && <BookOpen className="w-3.5 h-3.5 text-blue-600" />}
                      {isEBook && <FileText className="w-3.5 h-3.5 text-emerald-600" />}
                      {isAudio && <Headphones className="w-3.5 h-3.5 text-purple-600" />}
                      <span>{getFormatLabel(book.format)}</span>
                    </span>
                    <span aria-hidden="true">·</span>
                    <span className="truncate">{book.category}</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono text-slate-400 text-[11px]">{book.isbn.slice(-7)}</span>
                  </div>

                  {/* Title & Author */}
                  <h3 className="text-sm font-bold text-slate-900 leading-snug line-clamp-2">
                    {book.title}
                  </h3>
                  <div className="text-xs text-slate-600 mt-1">{book.author}</div>

                  {/* Description preview */}
                  {book.description && (
                    <p className="mt-2 text-xs text-slate-500 line-clamp-2 leading-relaxed">
                      {book.description}
                    </p>
                  )}

                  {/* Format details */}
                  <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
                    {isPhysical && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1 text-slate-500">
                            <MapPin className="w-3.5 h-3.5" /> Vị trí kệ:
                          </span>
                          <span className="font-medium text-slate-800">{book.shelf_location || 'A-01'}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1 text-slate-500">
                            <Scale className="w-3.5 h-3.5" /> Trọng lượng:
                          </span>
                          <span className="font-mono tabular-nums">{book.weight_grams || 350}g</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Tồn kho hiện có:</span>
                          <span
                            className={`font-mono tabular-nums font-semibold ${
                              isLowStock ? 'text-rose-600 font-bold' : 'text-slate-800'
                            }`}
                          >
                            {book.stock} cuốn {isLowStock && '(Sắp hết!)'}
                          </span>
                        </div>
                      </>
                    )}

                    {isEBook && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Dung lượng file:</span>
                          <span className="font-mono tabular-nums">{book.file_size_mb || 10} MB ({book.file_format || 'PDF'})</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Giao nhận:</span>
                          <span className="text-emerald-700 font-medium">Tải về trực tuyến (0đ phí ship)</span>
                        </div>
                      </>
                    )}

                    {isAudio && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1 text-slate-500">
                            <Clock className="w-3.5 h-3.5" /> Thời lượng:
                          </span>
                          <span className="font-mono tabular-nums">{book.duration_minutes || 300} phút</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1 text-slate-500">
                            <Mic className="w-3.5 h-3.5" /> Giọng đọc:
                          </span>
                          <span className="truncate max-w-[130px] font-medium text-slate-800">{book.narrator || 'Chuyên nghiệp'}</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Price & Action buttons */}
                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                  <div>
                    <span className="text-[11px] text-slate-400 block">Đơn giá</span>
                    <span className="text-base font-bold font-mono tabular-nums text-slate-900">
                      {formatCurrency(book.price)}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {isPhysical && (
                      <button
                        onClick={() => {
                          setRestockingBook(book);
                          setRestockAmount(10);
                        }}
                        title="Nhập thêm tồn kho"
                        className="p-1.5 text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-md transition-colors"
                      >
                        <PackagePlus className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleOpenEdit(book)}
                      title="Chỉnh sửa thông tin sách"
                      className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Bạn có chắc chắn muốn xóa cuốn sách "${book.title}" khỏi kho?`)) {
                          onDeleteBook(book.id);
                        }
                      }}
                      title="Xóa sách"
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL: Add / Edit Book */}
      {(isAddModalOpen || editingBook) && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {editingBook ? 'Chỉnh Sửa Thông Tin Sách' : 'Thêm Sách Mới Vào Kho'}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Chọn loại hình ấn bản: Sách in giấy, E-Book hoặc Sách nói
                </p>
              </div>
              <button
                onClick={() => {
                  setIsAddModalOpen(false);
                  setEditingBook(null);
                }}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {errorMsg && (
              <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmitBook} className="mt-4 space-y-4">
              {/* Format selection */}
              {!editingBook && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Định dạng sách
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setFormFormat('PHYSICAL')}
                      className={`p-3 text-left rounded-lg border text-xs transition-colors ${
                        formFormat === 'PHYSICAL'
                          ? 'border-slate-900 bg-slate-50 font-semibold text-slate-900'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      <div className="font-bold flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-blue-600" />
                        <span>Sách in</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">Sách giấy có vị trí kệ & số lượng tồn kho</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormFormat('EBOOK')}
                      className={`p-3 text-left rounded-lg border text-xs transition-colors ${
                        formFormat === 'EBOOK'
                          ? 'border-slate-900 bg-slate-50 font-semibold text-slate-900'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      <div className="font-bold flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-emerald-600" />
                        <span>E-Book</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">Sách điện tử, file PDF/EPUB, giao tức thì</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormFormat('AUDIOBOOK')}
                      className={`p-3 text-left rounded-lg border text-xs transition-colors ${
                        formFormat === 'AUDIOBOOK'
                          ? 'border-slate-900 bg-slate-50 font-semibold text-slate-900'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      <div className="font-bold flex items-center gap-1.5">
                        <Headphones className="w-3.5 h-3.5 text-purple-600" />
                        <span>Sách nói</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">Audio book có giọng đọc & thời lượng nghe</div>
                    </button>
                  </div>
                </div>
              )}

              {/* General fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Tên tựa sách <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder="VD: Cấu Trúc Dữ Liệu & Giải Thuật"
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Tác giả <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formAuthor}
                    onChange={(e) => setFormAuthor(e.target.value)}
                    placeholder="VD: Nguyễn Văn A"
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Thể loại</label>
                  <input
                    type="text"
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                    placeholder="VD: Văn học, Kinh tế, Công nghệ..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Giá bán (VND) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    required
                    value={formPrice}
                    onChange={(e) => setFormPrice(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none font-mono tabular-nums"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Nhà xuất bản</label>
                  <input
                    type="text"
                    value={formPublisher}
                    onChange={(e) => setFormPublisher(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                  />
                </div>
              </div>

              {/* Format-specific fields */}
              {formFormat === 'PHYSICAL' && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                  <span className="text-xs font-bold text-slate-900 block">
                    Thông tin sách in giấy
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Số lượng tồn kho ban đầu</label>
                      <input
                        type="number"
                        min="0"
                        value={formStock}
                        onChange={(e) => setFormStock(Number(e.target.value))}
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Trọng lượng (gam)</label>
                      <input
                        type="number"
                        min="50"
                        value={formWeight}
                        onChange={(e) => setFormWeight(Number(e.target.value))}
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Vị trí kệ sách</label>
                      <input
                        type="text"
                        value={formShelf}
                        onChange={(e) => setFormShelf(e.target.value)}
                        placeholder="Kệ A-01"
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white"
                      />
                    </div>
                  </div>
                </div>
              )}

              {formFormat === 'EBOOK' && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                  <span className="text-xs font-bold text-slate-900 block">
                    Thông tin ấn bản điện tử
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Dung lượng file (MB)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formFileSize}
                        onChange={(e) => setFormFileSize(Number(e.target.value))}
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Định dạng file</label>
                      <select
                        value={formFileFormat}
                        onChange={(e) => setFormFileFormat(e.target.value)}
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white"
                      >
                        <option value="PDF">PDF</option>
                        <option value="EPUB">EPUB</option>
                        <option value="MOBI">MOBI</option>
                      </select>
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-xs text-slate-600 mb-1">Đường dẫn tải sách</label>
                      <input
                        type="text"
                        value={formDownloadLink}
                        onChange={(e) => setFormDownloadLink(e.target.value)}
                        placeholder="https://..."
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white"
                      />
                    </div>
                  </div>
                </div>
              )}

              {formFormat === 'AUDIOBOOK' && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                  <span className="text-xs font-bold text-slate-900 block">
                    Thông tin sách nói
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Thời lượng (phút)</label>
                      <input
                        type="number"
                        min="1"
                        value={formDuration}
                        onChange={(e) => setFormDuration(Number(e.target.value))}
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Giọng đọc thuyết minh</label>
                      <input
                        type="text"
                        value={formNarrator}
                        onChange={(e) => setFormNarrator(e.target.value)}
                        placeholder="VD: NSƯT Hà Phương"
                        className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded bg-white"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Tóm tắt nội dung</label>
                <textarea
                  rows={2}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Giới thiệu nội dung tóm tắt..."
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-slate-900 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setIsAddModalOpen(false);
                    setEditingBook(null);
                  }}
                  className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50"
                >
                  {isSubmitting ? 'Đang lưu...' : editingBook ? 'Lưu Thay Đổi' : 'Thêm Vào Kho Sách'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Restock Book */}
      {restockingBook && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Nhập Thêm Tồn Kho</h3>
              <button
                onClick={() => {
                  setRestockingBook(null);
                  if (onClearPreselectedRestock) onClearPreselectedRestock();
                }}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRestockSubmit} className="mt-4 space-y-4">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                <div className="font-bold text-slate-900">{restockingBook.title}</div>
                <div className="text-slate-500">
                  Tác giả: {restockingBook.author} · Vị trí: {restockingBook.shelf_location || 'Kho'}
                </div>
                <div className="text-slate-700 font-medium">
                  Tồn kho hiện tại:{' '}
                  <span className="font-mono tabular-nums font-bold text-rose-600">
                    {restockingBook.stock}
                  </span>{' '}
                  cuốn
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Số lượng nhập thêm vào kho
                </label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  required
                  value={restockAmount}
                  onChange={(e) => setRestockAmount(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg font-mono tabular-nums focus:ring-2 focus:ring-slate-900 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setRestockingBook(null);
                    if (onClearPreselectedRestock) onClearPreselectedRestock();
                  }}
                  className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
                >
                  Đóng
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50"
                >
                  {isSubmitting ? 'Đang cập nhật...' : `Xác Nhận Nhập +${restockAmount} Cuốn`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
