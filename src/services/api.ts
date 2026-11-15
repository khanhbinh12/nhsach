import { Book, Customer, Order, Statistics, OOPArchitecture } from '../types';

export const api = {
  // Books & Inventory
  async getBooks(params?: { q?: string; category?: string; format?: string }): Promise<Book[]> {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set('q', params.q);
    if (params?.category) searchParams.set('category', params.category);
    if (params?.format) searchParams.set('format', params.format);

    const res = await fetch(`/api/books?${searchParams.toString()}`);
    if (!res.ok) throw new Error('Không thể tải danh sách sách');
    const data = await res.json();
    return data.books || [];
  },

  async getBook(id: string): Promise<Book> {
    const res = await fetch(`/api/books/${id}`);
    if (!res.ok) throw new Error('Không tìm thấy thông tin sách');
    const data = await res.json();
    return data.book;
  },

  async createBook(bookData: Partial<Book>): Promise<Book> {
    const res = await fetch('/api/books', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bookData),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Lỗi khi tạo sách mới');
    return data.book;
  },

  async updateBook(id: string, bookData: Partial<Book>): Promise<Book> {
    const res = await fetch(`/api/books/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bookData),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Lỗi cập nhật sách');
    return data.book;
  },

  async deleteBook(id: string): Promise<void> {
    const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Lỗi xóa sách');
  },

  async restockBook(id: string, quantity: number): Promise<Book> {
    const res = await fetch(`/api/books/${id}/restock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Lỗi nhập kho');
    return data.book;
  },

  async getCategories(): Promise<string[]> {
    const res = await fetch('/api/categories');
    if (!res.ok) return [];
    const data = await res.json();
    return data.categories || [];
  },

  // Customers
  async getCustomers(): Promise<Customer[]> {
    const res = await fetch('/api/customers');
    if (!res.ok) throw new Error('Lỗi khi tải danh sách khách hàng');
    const data = await res.json();
    return data.customers || [];
  },

  async createCustomer(cust: {
    name: string;
    phone: string;
    email: string;
    is_vip: boolean;
    tier?: string;
  }): Promise<Customer> {
    const res = await fetch('/api/customers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cust),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Lỗi tạo khách hàng');
    return data.customer;
  },

  // Orders
  async getOrders(): Promise<Order[]> {
    const res = await fetch('/api/orders');
    if (!res.ok) throw new Error('Lỗi khi tải danh sách hóa đơn');
    const data = await res.json();
    return data.orders || [];
  },

  async createOrder(payload: {
    customer_id?: string | null;
    customer_info?: { name: string; phone: string; email?: string };
    shipping_address?: string;
    order_type?: 'ONLINE' | 'POS';
    items: { id: string; quantity: number }[];
    discount_code: string;
    payment_method: string;
  }): Promise<Order> {
    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Lỗi thanh toán đơn hàng');
    return data.order;
  },

  // Statistics
  async getStats(): Promise<Statistics> {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error('Lỗi tải thống kê');
    const data = await res.json();
    return data.stats;
  },

  // OOP Metadata & Python Runner
  async getOOPArchitecture(): Promise<OOPArchitecture> {
    const res = await fetch('/api/oop-architecture');
    if (!res.ok) throw new Error('Lỗi tải thông tin kiến trúc OOP');
    const data = await res.json();
    return data.architecture;
  },

  async getSourceCode(): Promise<string> {
    const res = await fetch('/api/source-code');
    if (!res.ok) throw new Error('Lỗi tải mã nguồn Python');
    const data = await res.json();
    return data.code;
  },

  async executePython(code: string): Promise<{ success: boolean; output: string }> {
    const res = await fetch('/api/execute-python', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    const data = await res.json();
    return {
      success: data.success,
      output: data.output || data.error || 'Không có phản hồi từ máy chủ Python',
    };
  },

  async resetData(): Promise<void> {
    const res = await fetch('/api/reset-data', { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error('Lỗi khi đặt lại dữ liệu');
  },
};
