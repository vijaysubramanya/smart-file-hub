import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Function to get CSRF token from cookies
function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'X-CSRFToken': getCsrfToken(),
  },
});

// Update CSRF token on every request
api.interceptors.request.use(config => {
  config.headers['X-CSRFToken'] = getCsrfToken();
  return config;
});

export interface FileResponse {
  id: string;
  name: string;
  size: number;
  content_type: string;
  created_at: string;
  updated_at: string;
  url: string;
  is_original: boolean;
  original_file_url: string | null;
}

export interface PaginatedResponse<T> {
  results: T[];
  total: number;
  pages: number;
  current_page: number;
  is_superuser: boolean;
}

interface FilterState {
  minSize: string;
  maxSize: string;
  type: string;
  dateFrom: string;
  dateTo: string;
}

export interface StorageSavings {
  bytes_saved: number;
  human_readable_saved: string;
  duplicate_count: number;
}

export const fileService = {
  async list(page = 1, search = '', filters?: FilterState): Promise<PaginatedResponse<FileResponse>> {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    if (search) params.append('search', search);
    
    // Add filters if they exist
    if (filters) {
      if (filters.minSize) params.append('min_size', filters.minSize);
      if (filters.maxSize) params.append('max_size', filters.maxSize);
      if (filters.type) params.append('type', filters.type);
      if (filters.dateFrom) params.append('date_from', filters.dateFrom);
      if (filters.dateTo) params.append('date_to', filters.dateTo);
    }
    
    const response = await api.get<PaginatedResponse<FileResponse>>(`/files/?${params}`);
    return response.data;
  },

  async upload(file: File): Promise<FileResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<FileResponse>('/files/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/files/${id}/`);
  },

  async download(id: string): Promise<Blob> {
    const response = await api.get(`/files/${id}/download/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  async login(username: string, password: string): Promise<void> {
    try {
      // Get CSRF token first
      await api.get('/auth/csrf/');
      
      // Then attempt login with explicit content type
      const response = await api.post('/auth/login/', 
        { username, password },
        {
          headers: {
            'Content-Type': 'application/json',
          }
        }
      );
      
      console.log('Login response:', response.data);
    } catch (error: any) {
      console.error('Login error:', error.response?.data || error.message);
      throw error;
    }
  },

  async logout(): Promise<void> {
    await api.post('/auth/logout/');
    delete api.defaults.headers.common['Authorization'];
  },

  async getStorageSavings(): Promise<StorageSavings> {
    const response = await api.get<StorageSavings>('/files/storage_savings/');
    return response.data;
  },
};

// Add request interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
); 