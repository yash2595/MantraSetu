import apiClient from '@/api/api';

export interface LoginPayload {
  email: string;
  password: string;
  remember?: boolean;
}

export interface SignupPayload {
  user_type?: 'devotee' | 'pandit';
  name: string;
  email: string;
  phone?: string;
  password?: string;
  confirm_password?: string;
  city?: string;
  state?: string;
  languages?: string[];
  experience?: string;
  specialization?: string;
  aadhaar_file?: string | null;
  certificate_file?: string | null;
}

export interface PanditApplyPayload {
  name: string;
  email: string;
  phone?: string;
  password?: string;
  confirm_password?: string;
  city?: string;
  state?: string;
  // Step 1 extras
  gender?: string;
  availability_mode?: string;
  service_areas?: string[];
  // Step 2 qualifications
  languages?: string[];
  experience?: string;
  specializations?: string[];   // List[str] – multi-select
  education?: string;
  gurukul?: string;
  achievements?: string[];
  bio?: string;
  // Step 3 files
  aadhaar_file?: File | null;
  certificate_file?: File | null;
  gallery_files?: File[];
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user?: {
    id?: string;
    name?: string;
    email?: string;
    user_type?: string;
  };
  message?: string;
}

export const authService = {
  /**
   * POST /auth/login
   */
  async login(payload: LoginPayload): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', {
      email: payload.email,
      password: payload.password,
    });

    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
    }

    return response.data;
  },

  /**
   * POST /auth/google
   */
  async googleLogin(credential: string): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/google', {
      credential,
    });

    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
    }

    return response.data;
  },

  /**
   * POST /auth/signup (Devotee Signup)
   */
  async signup(payload: SignupPayload): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/signup', payload);

    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
    }

    return response.data;
  },

  /**
   * POST /pandit/apply (Pandit Application via multipart/form-data)
   */
  async applyPandit(data: FormData | PanditApplyPayload): Promise<AuthResponse> {
    let formData: FormData;

    if (data instanceof FormData) {
      formData = data;
    } else {
      formData = new FormData();
      formData.append('name', data.name);
      formData.append('email', data.email);
      if (data.phone) formData.append('phone', data.phone);
      if (data.password) formData.append('password', data.password);
      if (data.confirm_password) formData.append('confirm_password', data.confirm_password);
      if (data.city) formData.append('city', data.city);
      if (data.state) formData.append('state', data.state);
      if (data.experience) formData.append('experience', data.experience);
      if (data.specialization) formData.append('specialization', data.specialization);

      if (data.languages && Array.isArray(data.languages)) {
        data.languages.forEach((lang) => {
          formData.append('languages', lang);
        });
      }

      if (data.aadhaar_file) {
        formData.append('aadhaar_file', data.aadhaar_file);
      }
      if (data.certificate_file) {
        formData.append('certificate_file', data.certificate_file);
      }
    }

    const response = await apiClient.post<AuthResponse>('/pandit/apply', formData);

    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('token', response.data.access_token);
    }

    return response.data;
  },

  /**
   * Helper: Get stored token
   */
  getToken(): string | null {
    return localStorage.getItem('access_token') || localStorage.getItem('token');
  },

  /**
   * Helper: Logout
   */
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
  },

  /**
   * GET /auth/me (Stub reserved for future development)
   */
  async getMe(): Promise<unknown> {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

export default authService;
