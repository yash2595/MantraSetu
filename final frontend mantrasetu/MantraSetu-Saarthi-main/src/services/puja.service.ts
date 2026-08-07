import apiClient from '@/api/api';

export interface BackendPujaItem {
  id: string;
  title: string;
  category: 'Home & Family' | 'Dosha & Planetary' | 'Wealth & Success' | 'Health & Protection' | string;
  duration: string;
  price: number;
  rating?: number;
  reviewsCount?: number;
  reviews_count?: number;
  image?: string;
  description: string;
  popular?: boolean;
}

export interface BookPujaPayload {
  puja_id: string;
  puja_title?: string;
  city: string;
  date: string;
  time: string;
  devotee_name: string;
  phone: string;
}

export interface BookPujaResponse {
  id?: string;
  booking_id?: string;
  status?: string;
  message?: string;
}

export const pujaService = {
  /**
   * GET /puja/list
   */
  async listPujas(): Promise<BackendPujaItem[]> {
    const response = await apiClient.get<BackendPujaItem[]>('/puja/list');
    return response.data;
  },

  /**
   * POST /puja/book
   */
  async bookPuja(payload: BookPujaPayload): Promise<BookPujaResponse> {
    const response = await apiClient.post<BookPujaResponse>('/puja/book', payload);
    return response.data;
  },

  /**
   * GET /puja/history (Stub reserved for future development)
   */
  async getPujaHistory(): Promise<unknown> {
    const response = await apiClient.get('/puja/history');
    return response.data;
  },
};

export default pujaService;
