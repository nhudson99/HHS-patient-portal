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
  attemptsRemaining?: number;
  minutesRemaining?: number;
  minutesLocked?: number;
  code?: string;
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
        attemptsRemaining: data?.attemptsRemaining,
        minutesRemaining: data?.minutesRemaining,
        minutesLocked: data?.minutesLocked,
        code: data?.code,
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

/**
 * Patient properties (clinical notes) API
 */
export const patientPropertiesApi = {
  async list(patientId: string) {
    return request<{ properties: import('@/types').PatientProperty[] }>(
      `/api/patient-properties/${patientId}`,
      { method: 'GET' },
    );
  },

  async create(patientId: string, payload: { name: string; description?: string }) {
    return request<{ property: import('@/types').PatientProperty }>(
      `/api/patient-properties/${patientId}`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
  },

  async update(
    patientId: string,
    propertyId: number,
    payload: { name?: string; description?: string; updated_at?: string },
  ) {
    return request<{ property: import('@/types').PatientProperty }>(
      `/api/patient-properties/${patientId}/${propertyId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
    );
  },

  async delete(patientId: string, propertyId: number) {
    return request<{ message: string }>(
      `/api/patient-properties/${patientId}/${propertyId}`,
      { method: 'DELETE' },
    );
  },
};

/**
 * Provider chart API (allergies, medications, problems, summary)
 */
export const chartApi = {
  async getSummary(patientId: string) {
    return request<{ summary: import('@/types').ChartSummary }>(
      `/api/chart/${patientId}/summary`,
      { method: 'GET' },
    );
  },

  async listAllergies(patientId: string) {
    return request<{ allergies: import('@/types').Allergy[] }>(
      `/api/chart/${patientId}/allergies`,
      { method: 'GET' },
    );
  },

  async createAllergy(
    patientId: string,
    payload: {
      allergen: string
      reaction?: string
      severity?: import('@/types').AllergySeverity
      status?: import('@/types').AllergyStatus
      notes?: string
    },
  ) {
    return request<{ allergy: import('@/types').Allergy }>(
      `/api/chart/${patientId}/allergies`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  async updateAllergy(
    patientId: string,
    allergyId: string,
    payload: Partial<{
      allergen: string
      reaction: string | null
      severity: import('@/types').AllergySeverity
      status: import('@/types').AllergyStatus
      notes: string | null
    }>,
  ) {
    return request<{ allergy: import('@/types').Allergy }>(
      `/api/chart/${patientId}/allergies/${allergyId}`,
      { method: 'PUT', body: JSON.stringify(payload) },
    );
  },

  async deleteAllergy(patientId: string, allergyId: string) {
    return request<{ message: string }>(
      `/api/chart/${patientId}/allergies/${allergyId}`,
      { method: 'DELETE' },
    );
  },

  async listMedications(patientId: string) {
    return request<{ medications: import('@/types').Medication[] }>(
      `/api/chart/${patientId}/medications`,
      { method: 'GET' },
    );
  },

  async createMedication(
    patientId: string,
    payload: {
      name: string
      dosage?: string
      frequency?: string
      route?: string
      status?: import('@/types').MedicationStatus
      start_date?: string | null
      end_date?: string | null
      notes?: string
    },
  ) {
    return request<{ medication: import('@/types').Medication }>(
      `/api/chart/${patientId}/medications`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  async updateMedication(
    patientId: string,
    medicationId: string,
    payload: Partial<{
      name: string
      dosage: string | null
      frequency: string | null
      route: string | null
      status: import('@/types').MedicationStatus
      start_date: string | null
      end_date: string | null
      notes: string | null
    }>,
  ) {
    return request<{ medication: import('@/types').Medication }>(
      `/api/chart/${patientId}/medications/${medicationId}`,
      { method: 'PUT', body: JSON.stringify(payload) },
    );
  },

  async deleteMedication(patientId: string, medicationId: string) {
    return request<{ message: string }>(
      `/api/chart/${patientId}/medications/${medicationId}`,
      { method: 'DELETE' },
    );
  },

  async listProblems(patientId: string) {
    return request<{ problems: import('@/types').Problem[] }>(
      `/api/chart/${patientId}/problems`,
      { method: 'GET' },
    );
  },

  async createProblem(
    patientId: string,
    payload: {
      name: string
      status?: import('@/types').ProblemStatus
      onset_date?: string | null
      resolved_date?: string | null
      notes?: string
    },
  ) {
    return request<{ problem: import('@/types').Problem }>(
      `/api/chart/${patientId}/problems`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  async updateProblem(
    patientId: string,
    problemId: string,
    payload: Partial<{
      name: string
      status: import('@/types').ProblemStatus
      onset_date: string | null
      resolved_date: string | null
      notes: string | null
    }>,
  ) {
    return request<{ problem: import('@/types').Problem }>(
      `/api/chart/${patientId}/problems/${problemId}`,
      { method: 'PUT', body: JSON.stringify(payload) },
    );
  },

  async deleteProblem(patientId: string, problemId: string) {
    return request<{ message: string }>(
      `/api/chart/${patientId}/problems/${problemId}`,
      { method: 'DELETE' },
    );
  },
};

/**
 * Documents API helpers (visibility toggle)
 */
export const documentsApi = {
  async setVisibility(docId: string, patientVisible: boolean) {
    return request<{ document: import('@/types').PatientDocument; message: string }>(
      `/api/documents/${docId}/visibility`,
      {
        method: 'PUT',
        body: JSON.stringify({ patient_visible: patientVisible }),
      },
    );
  },
};

/**
 * In-app messaging API (DMs, channels, threads)
 */
export const messagesApi = {
  async listConversations() {
    return request<{ conversations: import('@/types').Conversation[] }>(
      '/api/conversations',
      { method: 'GET' },
    );
  },

  async getUnreadCount() {
    return request<{ unread_count: number }>(
      '/api/conversations/unread-count',
      { method: 'GET' },
    );
  },

  async listContacts() {
    return request<{ contacts: import('@/types').MessagingContact[] }>(
      '/api/conversations/contacts',
      { method: 'GET' },
    );
  },

  async createConversation(payload: {
    type: 'dm' | 'channel';
    participant_user_id?: string;
    title?: string;
    participant_user_ids?: string[];
  }) {
    return request<{
      conversation: import('@/types').Conversation;
      created: boolean;
    }>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getConversation(conversationId: string) {
    return request<{ conversation: import('@/types').Conversation }>(
      `/api/conversations/${conversationId}`,
      { method: 'GET' },
    );
  },

  async listMessages(
    conversationId: string,
    options: {
      limit?: number;
      before?: string;
      since?: string;
      parent_message_id?: string;
      top_level_only?: boolean;
    } = {},
  ) {
    const params = new URLSearchParams();
    if (options.limit) params.set('limit', String(options.limit));
    if (options.before) params.set('before', options.before);
    if (options.since) params.set('since', options.since);
    if (options.parent_message_id) params.set('parent_message_id', options.parent_message_id);
    if (options.top_level_only === false) params.set('top_level_only', 'false');
    const query = params.toString();
    return request<{ messages: import('@/types').ChatMessage[]; has_more: boolean }>(
      `/api/conversations/${conversationId}/messages${query ? `?${query}` : ''}`,
      { method: 'GET' },
    );
  },

  async sendMessage(
    conversationId: string,
    payload: { body: string; parent_message_id?: string },
  ) {
    return request<{ message: import('@/types').ChatMessage }>(
      `/api/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
  },

  async markRead(conversationId: string) {
    return request<{ message: string; unread_count: number; read_at: string }>(
      `/api/conversations/${conversationId}/read`,
      { method: 'PATCH' },
    );
  },

  async addParticipants(conversationId: string, participantUserIds: string[]) {
    return request<{
      message: string;
      added_user_ids: string[];
      participants: import('@/types').ConversationParticipant[];
    }>(`/api/conversations/${conversationId}/participants`, {
      method: 'POST',
      body: JSON.stringify({ participant_user_ids: participantUserIds }),
    });
  },
};

export default {
  auth: authApi,
  health: healthApi,
  patientProperties: patientPropertiesApi,
  chart: chartApi,
  documents: documentsApi,
  messages: messagesApi,
};
