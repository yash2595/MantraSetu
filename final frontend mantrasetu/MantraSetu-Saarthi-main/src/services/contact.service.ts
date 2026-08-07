import apiClient from '@/api/api';

export interface ContactPayload {
  name: string;
  email: string;
  topic: string;
  message: string;
}

export interface ContactResponse {
  status: string;
  message: string;
  contact_id?: string;
}

export const contactService = {
  /**
   * POST /contact
   */
  async sendContactMessage(payload: ContactPayload): Promise<ContactResponse> {
    const response = await apiClient.post<ContactResponse>('/contact', payload);
    return response.data;
  },
};

export default contactService;
