export type BookFormat = 'PHYSICAL' | 'EBOOK' | 'AUDIOBOOK';

export interface Book {
  id: string;
  title: string;
  author: string;
  category: string;
  price: number;
  stock: number;
  isbn: string;
  publisher: string;
  publish_year: number;
  description: string;
  format: BookFormat;
  shipping_fee: number;
  // PhysicalBook fields
  weight_grams?: number;
  shelf_location?: string;
  cover_type?: string;
  // EBook fields
  file_size_mb?: number;
  file_format?: string;
  download_link?: string;
  // AudioBook fields
  duration_minutes?: number;
  narrator?: string;
  sample_audio_url?: string;
}

export type VIPTier = 'STANDARD' | 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM';

export interface Customer {
  id: string;
  name: string;
  phone: string;
  email: string;
  loyalty_points: number;
  total_spent: number;
  tier: VIPTier;
  discount_rate: number;
  joined_date: string;
  is_vip: boolean;
}

export interface OrderItem {
  item_id: string;
  title: string;
  author: string;
  format: BookFormat;
  quantity: number;
  unit_price: number;
  subtotal: number;
  shipping_fee: number;
}

export interface DiscountPolicyInfo {
  code: string;
  description: string;
}

export interface Order {
  id: string;
  created_at: string;
  customer: Customer | null;
  payment_method: string;
  shipping_address?: string;
  order_type?: 'ONLINE' | 'POS';
  discount_policy: DiscountPolicyInfo;
  items: OrderItem[];
  total_quantity: number;
  subtotal: number;
  discount_amount: number;
  shipping_fee: number;
  final_total: number;
  status: 'COMPLETED' | 'PENDING' | 'CANCELLED';
}

export interface TopSeller {
  title: string;
  format: BookFormat;
  category: string;
  total_sold: number;
  revenue: number;
}

export interface Statistics {
  total_revenue: number;
  total_orders: number;
  total_books_types: number;
  total_physical_stock: number;
  total_customers: number;
  low_stock_count: number;
  low_stock_items: Book[];
  top_sellers: TopSeller[];
  category_revenue: Record<string, number>;
}

export interface OOPPillar {
  name: string;
  description: string;
  examples: string[];
}

export interface OOPClassInfo {
  name: string;
  type: string;
  file: string;
  parent: string;
}

export interface OOPArchitecture {
  pillars: OOPPillar[];
  classes: OOPClassInfo[];
}
