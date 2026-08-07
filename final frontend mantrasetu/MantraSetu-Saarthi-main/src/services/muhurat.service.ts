import apiClient from '@/api/api';

export interface MuhuratFindPayload {
  event_type: string;
  city: string;
  date: string;
}

export interface TimingCardItem {
  type?: string;
  label?: string;
  time_range?: string;
  timeRange?: string;
  description: string;
  is_featured?: boolean;
  isFeatured?: boolean;
}

export interface MuhuratFindResponse {
  event_label?: string;
  eventLabel?: string;
  city_label?: string;
  cityLabel?: string;
  date?: string;
  timings?: TimingCardItem[];
  message?: string;
}

export const muhuratService = {
  /**
   * POST /muhurat/find
   */
  async findMuhurat(payload: MuhuratFindPayload): Promise<MuhuratFindResponse> {
    const response = await apiClient.post<MuhuratFindResponse>('/muhurat/find', payload);
    return response.data;
  },
};

export default muhuratService;
