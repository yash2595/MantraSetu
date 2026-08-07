import apiClient from '@/api/api';

export interface KundaliGeneratePayload {
  name: string;
  dob: string;
  tob?: string;
  pob: string;
  gender?: string;
}

export interface KundaliHouseItem {
  house: number;
  sign?: string;
  planets?: string[];
  description?: string;
}

export interface KundaliGenerateResponse {
  id?: string;
  name?: string;
  chart_title?: string;
  houses?: KundaliHouseItem[];
  planetary_positions?: Record<string, string>;
  dasha_info?: string;
  insights?: string[];
  note?: string;
  message?: string;
}

export const kundaliService = {
  /**
   * POST /kundali/generate
   */
  async generateKundali(payload: KundaliGeneratePayload): Promise<KundaliGenerateResponse> {
    const response = await apiClient.post<KundaliGenerateResponse>('/kundali/generate', payload);
    return response.data;
  },

  /**
   * GET /kundali/history (Stub reserved for future development)
   */
  async getKundaliHistory(): Promise<unknown> {
    const response = await apiClient.get('/kundali/history');
    return response.data;
  },
};

export default kundaliService;
