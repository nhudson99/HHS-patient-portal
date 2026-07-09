/**
 * API Service for HHS Patient Portal
 * Handles all HTTP requests to the Python Flask backend
 */

const API_BASE_URL = (import.meta as any).env.VITE_API_URL || '';
const API_REQUEST_TIMEOUT_MS = 15000;

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Make HTTP request with error handling
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const token = localStorage.getItem('sessionToken');
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    
    // Add authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const abortController = new AbortController();
    const timeoutId = globalThis.setTimeout(() => abortController.abort(), API_REQUEST_TIMEOUT_MS);

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      signal: abortController.signal,
    });

    globalThis.clearTimeout(timeoutId);

    let data: any = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      data = await response.json();
    }
    
    if (!response.ok) {
      return {
        error: data?.error || `HTTP ${response.status}: ${response.statusText}`,
      };
    }
    
    return { data };
  } catch (error) {
    console.error('API request failed:', error);
    return {
      error: error instanceof Error ? error.message : 'Network error occurred',
    };
  }
}

/**
 * Authentication API
 */
export const authApi = {
  /**
   * Login user with plaintext password over HTTPS/TLS.
   * Password verification is performed server-side.
   */
  async login(username: string, password: string): Promise<ApiResponse<{
    message: string;
    sessionToken: string;
    user: {
      id: string;
      username: string;
      email: string;
      role: string;
    };
    requirePasswordChange?: boolean;
  }>> {
    return request<{
      message: string;
      sessionToken: string;
      user: {
        id: string;
        username: string;
        email: string;
        role: string;
      };
      requirePasswordChange?: boolean;
    }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },
  
  /**
   * Register new user - sends plaintext password (over HTTPS in production)
   */
  async register(userData: {
    username: string;
    email: string;
    password: string;
    firstName: string;
    lastName: string;
    dateOfBirth: string;
    phone?: string;
  }) {
    // Send registration with plaintext password (backend will hash it)
    // In production, this should be over HTTPS/TLS
    return request<{
      message: string;
      user: {
        id: string;
        username: string;
        email: string;
        role: string;
      };
    }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },
  
  /**
   * Logout user
   */
  async logout() {
    const response = await request('/api/auth/logout', {
      method: 'POST',
    });
    
    // Clear local storage
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('currentUser');
    
    return response;
  },
  
  /**
   * Get current user
   */
  async getCurrentUser() {
    return request<{
      user: {
        id: string;
        username: string;
        email: string;
        role: string;
      };
    }>('/api/auth/me', {
      method: 'GET',
    });
  },
  
  /**
   * Change password - sends plaintext passwords (over HTTPS in production)
   */
  async changePassword(currentPassword: string, newPassword: string) {
    return request<{ message: string }>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        currentPassword,
        newPassword,
      }),
    });
  },
};

/**
 * Health check
 */
export const healthApi = {
  async check() {
    return request<{ status: string; timestamp: string }>('/health');
  },
};

export default {
  auth: authApi,
  health: healthApi,
};
