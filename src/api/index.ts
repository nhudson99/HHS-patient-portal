/**
 * API Service for HHS Patient Portal
 * Handles all HTTP requests to the Python Flask backend
 */

import bcryptjs from 'bcryptjs';

const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:3000';

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
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      return {
        error: data.error || `HTTP ${response.status}: ${response.statusText}`,
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
   * Get salt for a username (needed for client-side password hashing)
   */
  async getSalt(username: string) {
    return request<{
      salt: string;
    }>('/api/auth/salt', {
      method: 'POST',
      body: JSON.stringify({ username }),
    });
  },

  /**
   * Login user with client-side hashed password
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
    // Step 1: Get the bcrypt salt for this user
    const saltResponse = await this.getSalt(username);
    
    if (saltResponse.error) {
      return { error: saltResponse.error } as any;
    }
    
    const bcryptSalt = saltResponse.data?.salt;
    if (!bcryptSalt) {
      return { error: 'Failed to retrieve salt for hashing' };
    }
    
    // Step 2: Hash the password client-side using bcryptjs with the retrieved salt
    // The bcryptSalt is a full bcrypt salt string (e.g., "$2a$10$...")
    let hashedPassword: string;
    try {
      // bcryptjs.hash can use an existing salt by using it directly
      // We use hashSync to get consistent behavior
      hashedPassword = bcryptjs.hashSync(password, bcryptSalt);
    } catch (error) {
      console.error('Password hashing error:', error);
      return { error: 'Failed to hash password - invalid salt' };
    }
    
    // Step 3: Send the hashed password (plaintext password never leaves client)
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
      body: JSON.stringify({ username, password: hashedPassword }),
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
