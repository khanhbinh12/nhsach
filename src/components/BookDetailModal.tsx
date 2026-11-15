import React, { useState } from 'react';
import { Book } from '../types';
import { formatCurrency, getFormatLabel } from '../utils/formatters';
import {
  X,
  BookOpen,
  Headphones,
  FileText,
  ShoppingCart,
  Play,
  Pause,
  Download,
  Share2,
  Check,
  MapPin,
  Scale,
  Clock,
  Mic,
  ShieldCheck,
} from 'lucide-react';

interface BookDetailModalProps {
  book: Book | null;
  onClose: () => void;
  onAddToCart: (book: Book, quantity: number) => void;
  onBuyNow: (book: Book) => void;
}

export const BookDetailModal: React.FC<BookDetailModalProps> = ({
  book,
  onClose,
  onAddToCart,
  onBuyNow,
}) => {
  const [quantity, setQuantity] = useState(1);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioProgress, setAudioProgress] = useState(35);
  const [activeTab, setActiveTab] = useState<'info' | 'preview'>('info');
  const [copiedLink, setCopiedLink] = useState(false);

  if (!book) return null;

  const isPhysical = book.format === 'PHYSICAL';
  const isEBook = book.format === 'EBOOK';
  const isAudio = book.format === 'AUDIOBOOK';
  const isOutOfStock = isPhysical && book.stock <= 0;

  const togglePlayAudio = () => {
    setIsPlayingAudio(!isPlayingAudio);
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full p-6 sm:p-8 max-h-[90vh] overflow-y-auto relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          {/* Book Spine & Cover Representation (5 cols) */}
          <div className="md:col-span-5 flex flex-col items-center">
            <div className="w-full max-w-[240px] aspect-[3/4] rounded-xl bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 p-6 flex flex-col justify-between text-white shadow-xl relative overflow-hidden group border border-slate-700">
              {/* Spine shadow effect */}
              <div className="absolute left-0 top-0 bottom-0 w-4 bg-gradient-to-r from-black/60 via-black/20 to-transparent pointer-events-none" />

              <div className="space-y-1">
                <span className="text-[11px] font-mono tracking-wider text-amber-400 uppercase font-semibold">
                  {getFormatLabel(book.format)}
                </span>
                <div className="text-[10px] text-slate-400 font-mono">{book.category}</div>
              </div>

              <div className="my-auto py-4">
                <h3 className="font-bold text-base text-white leading-snug line-clamp-3">
                  {book.title}
                </h3>
                <div className="text-xs text-slate-300 mt-2 font-medium">{book.author}</div>
              </div>

              <div className="pt-3 border-t border-slate-700/60 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                <span>{book.publisher}</span>
                <span>{book.publish_year}</span>
              </div>
            </div>

            {/* Quick Share / Format indicator */}
            <div className="mt-4 flex items-center gap-2">
              <button
                onClick={handleShare}
                className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center gap-1.5 transition-colors"
              >
                {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Share2 className="w-3.5 h-3.5" />}
                <span>{copiedLink ? 'Đã chép link' : 'Chia sẻ tựa sách'}</span>
              </button>
            </div>
          </div>

          {/* Book Information & Actions (7 cols) */}
          <div className="md:col-span-7 space-y-5">
            <div>
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-1.5">
                <span className="font-semibold text-slate-800">{book.category}</span>
                <span>·</span>
                <span>NXB {book.publisher}</span>
                <span>·</span>
                <span>Năm {book.publish_year}</span>
              </div>

              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 leading-snug">
                {book.title}
              </h1>

              <div className="text-sm font-medium text-slate-700 mt-1">
                Tác giả: <span className="font-semibold text-slate-900">{book.author}</span>
              </div>
            </div>

            {/* Pricing strip */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-500 block">Giá bán ưu đãi</span>
                <span className="text-2xl font-bold font-mono tabular-nums text-indigo-700">
                  {formatCurrency(book.price)}
                </span>
              </div>
              <div>
                {isPhysical ? (
                  <span
                    className={`text-xs font-semibold px-2.5 py-1 rounded-md ${
                      isOutOfStock
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {isOutOfStock ? 'Tạm hết hàng' : `Còn ${book.stock} cuốn trong kho`}
                  </span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200">
                    Sở hữu & Đọc ngay
                  </span>
                )}
              </div>
            </div>

            {/* Format-specific details */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              {isPhysical && (
                <>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 flex items-center gap-1">
                      <Scale className="w-3.5 h-3.5" /> Trọng lượng:
                    </span>
                    <span className="font-semibold text-slate-800 font-mono mt-0.5 block">
                      {book.weight_grams || 350} gam
                    </span>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> Vị trí kệ:
                    </span>
                    <span className="font-semibold text-slate-800 mt-0.5 block">
                      {book.shelf_location || 'Kệ trung tâm'}
                    </span>
                  </div>
                </>
              )}

              {isEBook && (
                <>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500">Dung lượng:</span>
                    <span className="font-semibold text-slate-800 font-mono mt-0.5 block">
                      {book.file_size_mb || 10} MB ({book.file_format || 'PDF'})
                    </span>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500">Giao nhận:</span>
                    <span className="font-semibold text-emerald-700 mt-0.5 block">
                      Tải file trực tuyến ngay
                    </span>
                  </div>
                </>
              )}

              {isAudio && (
                <>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Thời lượng:
                    </span>
                    <span className="font-semibold text-slate-800 font-mono mt-0.5 block">
                      {book.duration_minutes || 360} phút
                    </span>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 flex items-center gap-1">
                      <Mic className="w-3.5 h-3.5" /> Giọng đọc:
                    </span>
                    <span className="font-semibold text-slate-800 mt-0.5 block truncate">
                      {book.narrator || 'Chuyên nghiệp'}
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Audio Sample Player for AudioBooks */}
            {isAudio && (
              <div className="p-3.5 bg-purple-50/70 border border-purple-200 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold text-purple-900">
                  <span className="flex items-center gap-1.5">
                    <Headphones className="w-4 h-4 text-purple-700" />
                    Nghe thử một đoạn audio mẫu
                  </span>
                  <span className="text-purple-600 font-mono">03:45 / 12:00</span>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={togglePlayAudio}
                    className="w-8 h-8 rounded-full bg-purple-700 text-white flex items-center justify-center hover:bg-purple-800 transition-colors shrink-0 shadow-xs"
                  >
                    {isPlayingAudio ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                  </button>
                  <div className="flex-1 h-2 bg-purple-200 rounded-full overflow-hidden cursor-pointer">
                    <div
                      className="h-full bg-purple-700 rounded-full transition-all duration-200"
                      style={{ width: `${audioProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Description / Synopsis */}
            <div>
              <h4 className="text-xs font-bold text-slate-900 mb-1">Giới thiệu nội dung</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                {book.description ||
                  'Tác phẩm mang lại góc nhìn sâu sắc và giá trị nhân văn cao, được tuyển chọn và phát hành chính hãng tại Nhà Sách Trí Tri.'}
              </p>
            </div>

            {/* Purchase action strip */}
            <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-center gap-3">
              {isPhysical && !isOutOfStock && (
                <div className="flex items-center border border-slate-200 rounded-lg p-1 bg-white shrink-0">
                  <button
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="w-7 h-7 flex items-center justify-center text-slate-600 hover:bg-slate-100 rounded"
                  >
                    -
                  </button>
                  <span className="w-8 text-center font-mono font-bold text-xs text-slate-900">
                    {quantity}
                  </span>
                  <button
                    onClick={() => setQuantity(Math.min(book.stock, quantity + 1))}
                    className="w-7 h-7 flex items-center justify-center text-slate-600 hover:bg-slate-100 rounded"
                  >
                    +
                  </button>
                </div>
              )}

              <button
                onClick={() => {
                  onAddToCart(book, quantity);
                  onClose();
                }}
                disabled={isOutOfStock}
                className="w-full sm:flex-1 py-2.5 px-4 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <ShoppingCart className="w-4 h-4" />
                <span>Thêm Vào Giỏ Hàng</span>
              </button>

              <button
                onClick={() => {
                  onBuyNow(book);
                  onClose();
                }}
                disabled={isOutOfStock}
                className="w-full sm:flex-1 py-2.5 px-4 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50 shadow-xs"
              >
                Mua Ngay
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
