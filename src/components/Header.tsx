import React from 'react';
import {
  BookOpen,
  RotateCcw,
  FileCode,
  ShoppingCart,
  Store,
  LayoutDashboard,
} from 'lucide-react';

export type AppMode = 'storefront' | 'admin';
export type AdminTab = 'dashboard' | 'inventory' | 'pos' | 'customers' | 'orders';

interface HeaderProps {
  appMode: AppMode;
  setAppMode: (mode: AppMode) => void;
  adminTab: AdminTab;
  setAdminTab: (tab: AdminTab) => void;
  onResetData: () => void;
  isResetting: boolean;
  onOpenTechDocs: () => void;
  cartCount: number;
  onOpenCart: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  appMode,
  setAppMode,
  adminTab,
  setAdminTab,
  onResetData,
  isResetting,
  onOpenTechDocs,
  cartCount,
  onOpenCart,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-8 h-16">
          {/* Zone 1: Single text wordmark */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-amber-400 flex items-center justify-center shadow-xs">
              <BookOpen className="w-4 h-4" />
            </div>
            <a
              href="#store"
              onClick={(e) => {
                e.preventDefault();
                setAppMode('storefront');
              }}
              className="text-base font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0 hover:text-slate-700 transition-colors"
            >
              Nhà Sách Trí Tri
            </a>
          </div>

          {/* Zone 2: Navigation Links depending on App Mode */}
          {appMode === 'storefront' ? (
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
              <span className="text-slate-900 font-semibold border-b-2 border-slate-900 py-1 whitespace-nowrap shrink-0">
                Cửa Hàng Trực Tuyến
              </span>
              <a
                href="#bestsellers"
                onClick={(e) => {
                  e.preventDefault();
                  // scroll to catalog
                }}
                className="hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1"
              >
                Sách Tuyển Chọn
              </a>
              <button
                onClick={() => {
                  setAppMode('admin');
                  setAdminTab('dashboard');
                }}
                className="text-slate-500 hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1 flex items-center gap-1.5"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Bàn Quản Trị Nhà Sách</span>
              </button>
            </nav>
          ) : (
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
              <button
                onClick={() => setAdminTab('dashboard')}
                className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
                  adminTab === 'dashboard'
                    ? 'border-slate-900 text-slate-900 font-semibold'
                    : 'border-transparent'
                }`}
              >
                Tổng Quan
              </button>
              <button
                onClick={() => setAdminTab('inventory')}
                className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
                  adminTab === 'inventory'
                    ? 'border-slate-900 text-slate-900 font-semibold'
                    : 'border-transparent'
                }`}
              >
                Kho Sách
              </button>
              <button
                onClick={() => setAdminTab('pos')}
                className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
                  adminTab === 'pos'
                    ? 'border-slate-900 text-slate-900 font-semibold'
                    : 'border-transparent'
                }`}
              >
                Bán Hàng (POS)
              </button>
              <button
                onClick={() => setAdminTab('customers')}
                className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
                  adminTab === 'customers'
                    ? 'border-slate-900 text-slate-900 font-semibold'
                    : 'border-transparent'
                }`}
              >
                Khách Hàng
              </button>
              <button
                onClick={() => setAdminTab('orders')}
                className={`hover:text-slate-900 transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
                  adminTab === 'orders'
                    ? 'border-slate-900 text-slate-900 font-semibold'
                    : 'border-transparent'
                }`}
              >
                Hóa Đơn
              </button>
              <button
                onClick={() => setAppMode('storefront')}
                className="text-indigo-600 hover:text-indigo-800 transition-colors whitespace-nowrap shrink-0 py-1 flex items-center gap-1.5"
              >
                <Store className="w-3.5 h-3.5" />
                <span>Xem Cửa Hàng</span>
              </button>
            </nav>
          )}

          {/* Zone 3: Primary Action & Controls */}
          <div className="flex items-center gap-3 shrink-0">
            {/* Tech Docs toggle */}
            <button
              onClick={onOpenTechDocs}
              title="Xem hồ sơ kiến trúc backend Python OOP"
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
            >
              <FileCode className="w-3.5 h-3.5 text-indigo-600" />
              <span>Hồ sơ kỹ thuật</span>
            </button>

            {/* Reset data */}
            <button
              onClick={onResetData}
              disabled={isResetting}
              title="Đặt lại dữ liệu mẫu về ban đầu"
              className="p-2 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <RotateCcw className={`w-4 h-4 ${isResetting ? 'animate-spin' : ''}`} />
            </button>

            {/* Shopping Cart button in Storefront mode */}
            {appMode === 'storefront' ? (
              <button
                onClick={onOpenCart}
                className="relative px-3.5 py-2 text-xs font-semibold text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-2"
              >
                <ShoppingCart className="w-4 h-4" />
                <span className="hidden sm:inline">Giỏ hàng</span>
                {cartCount > 0 && (
                  <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono text-[10px] flex items-center justify-center font-bold">
                    {cartCount}
                  </span>
                )}
              </button>
            ) : (
              <button
                onClick={() => {
                  setAppMode('admin');
                  setAdminTab('pos');
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shadow-xs"
              >
                Thu Ngân Tại Quầy
              </button>
            )}

            {/* Mode Switch button */}
            <button
              onClick={() => setAppMode(appMode === 'storefront' ? 'admin' : 'storefront')}
              className={`px-3 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                appMode === 'storefront'
                  ? 'bg-slate-900 text-white hover:bg-slate-800 shadow-xs'
                  : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
              }`}
            >
              {appMode === 'storefront' ? 'Vào Quản Trị' : 'Cửa Hàng Khách'}
            </button>
          </div>
        </div>

        {/* Mobile secondary navigation */}
        <div className="flex md:hidden overflow-x-auto gap-4 py-2 text-xs border-t border-slate-100 scrollbar-none">
          <button
            onClick={() => setAppMode('storefront')}
            className={`whitespace-nowrap px-2 py-1 ${appMode === 'storefront' ? 'font-bold text-slate-900' : 'text-slate-500'}`}
          >
            Cửa Hàng Sách
          </button>
          <button
            onClick={() => {
              setAppMode('admin');
              setAdminTab('dashboard');
            }}
            className={`whitespace-nowrap px-2 py-1 ${appMode === 'admin' && adminTab === 'dashboard' ? 'font-bold text-slate-900' : 'text-slate-500'}`}
          >
            Tổng Quan
          </button>
          <button
            onClick={() => {
              setAppMode('admin');
              setAdminTab('inventory');
            }}
            className={`whitespace-nowrap px-2 py-1 ${appMode === 'admin' && adminTab === 'inventory' ? 'font-bold text-slate-900' : 'text-slate-500'}`}
          >
            Kho Sách
          </button>
          <button
            onClick={() => {
              setAppMode('admin');
              setAdminTab('pos');
            }}
            className={`whitespace-nowrap px-2 py-1 ${appMode === 'admin' && adminTab === 'pos' ? 'font-bold text-slate-900' : 'text-slate-500'}`}
          >
            Thu Ngân
          </button>
          <button
            onClick={() => {
              setAppMode('admin');
              setAdminTab('orders');
            }}
            className={`whitespace-nowrap px-2 py-1 ${appMode === 'admin' && adminTab === 'orders' ? 'font-bold text-slate-900' : 'text-slate-500'}`}
          >
            Hóa Đơn
          </button>
        </div>
      </div>
    </header>
  );
};
