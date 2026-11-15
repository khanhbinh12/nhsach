import { BookFormat, VIPTier } from '../types';

export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(amount);
};

export const getFormatLabel = (format: BookFormat): string => {
  switch (format) {
    case 'PHYSICAL':
      return 'Sách in';
    case 'EBOOK':
      return 'E-Book';
    case 'AUDIOBOOK':
      return 'Sách nói';
    default:
      return format;
  }
};

export const getTierLabel = (tier: VIPTier): string => {
  switch (tier) {
    case 'PLATINUM':
      return 'VIP Kim Cương (Giảm 20%)';
    case 'GOLD':
      return 'VIP Vàng (Giảm 15%)';
    case 'SILVER':
      return 'VIP Bạc (Giảm 10%)';
    case 'BRONZE':
      return 'VIP Đồng (Giảm 5%)';
    case 'STANDARD':
    default:
      return 'Thành viên thường';
  }
};
