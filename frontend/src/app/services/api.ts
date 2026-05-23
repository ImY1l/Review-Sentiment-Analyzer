/**
 * API Service Layer for connecting to FastAPI Backend
 * 
 * Replace the BASE_URL with your FastAPI backend URL
 * Example: http://localhost:8000 or https://your-backend.com
 */

const BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Helper function for making API requests
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  
  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// ============================================================================
// AUTHENTICATION APIs
// ============================================================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  username: string;
  name?: string;
  email?: string;
  role: 'user' | 'admin';
  token?: string; // Optional: if you use JWT tokens
}

export interface RegisterRequest {
  name: string;
  email: string;
  username: string;
  password: string;
}

export interface RegisterResponse {
  success: boolean;
  message?: string;
}

/**
 * Login user
 * FastAPI endpoint: POST /api/auth/login
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Register new user
 * FastAPI endpoint: POST /api/auth/register
 */
export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============================================================================
// SEARCH & ANALYSIS APIs
// ============================================================================

export interface SearchRequest {
  query: string;
  category: string;
  platforms: string[];
}

export interface AnalysisResult {
  summary: string;
  pros: string[];
  cons: string[];
  sentimentData: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  ratingData: Array<{
    rating: string;
    count: number;
    percentage: number;
  }>;
  trendData: Array<{
    month: string;
    positive: number;
    negative: number;
    neutral: number;
  }>;
  topicsData: Array<{
    topic: string;
    mentions: number;
  }>;
}

/**
 * Unified search: scrape selected platforms + analyze
 * FastAPI endpoint: POST /api/search
 */
export async function unifiedSearch(data: {
  query: string;
  user_id: string;
  platforms: string[];
}): Promise<{
  success: boolean;
  product_id?: string;
  product_ids?: string[];
  platforms?: string[];
  analysis?: any;
  message?: string;
}> {
  return apiRequest('/api/search', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Legacy analyzeReviews (kept for compatibility)
 */
export async function analyzeReviews(data: SearchRequest): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>('/api/reviews/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function validateSearch(data: SearchRequest): Promise<{ valid: boolean; message?: string }> {
  return { valid: true };
}

// ============================================================================
// ADMIN APIs - System Logs
// ============================================================================

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  action: string;
  details: string;
  user?: string;
}

/**
 * Get system logs
 * FastAPI endpoint: GET /api/admin/logs
 */
export async function getLogs(params?: {
  level?: string;
  limit?: number;
  offset?: number;
}): Promise<LogEntry[]> {
  const queryParams = new URLSearchParams();
  if (params?.level && params.level !== 'all') queryParams.append('level', params.level);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  
  const query = queryParams.toString();
  return apiRequest<LogEntry[]>(`/api/admin/logs${query ? `?${query}` : ''}`);
}

// ============================================================================
// ADMIN APIs - User Management
// ============================================================================

export interface User {
  id: string;
  name: string;
  email: string;
  username: string;
  dateJoined: string;
  searchCount: number;
}

/**
 * Get all users
 * FastAPI endpoint: GET /api/admin/users
 */
export async function getUsers(): Promise<User[]> {
  return apiRequest<User[]>('/api/admin/users');
}

/**
 * Add new user
 * FastAPI endpoint: POST /api/admin/users
 */
export type AdminAddUserRequest = {
  name: string;
  email: string;
  username: string;
  password: string;
  role: 'user' | 'admin';
  dateJoined?: string;
  searchCount?: number;
};

export async function addUser(user: AdminAddUserRequest): Promise<User> {
  return apiRequest<User>('/api/admin/users', {
    method: 'POST',
    body: JSON.stringify(user),
  });
}


/**
 * Update user
 * FastAPI endpoint: PUT /api/admin/users/{userId}
 */
export async function updateUser(userId: string, user: Partial<User>): Promise<User> {
  return apiRequest<User>(`/api/admin/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(user),
  });
}

/**
 * Delete user
 * FastAPI endpoint: DELETE /api/admin/users/{userId}
 */
export async function deleteUser(userId: string): Promise<{ success: boolean }> {
  return apiRequest(`/api/admin/users/${userId}`, {
    method: 'DELETE',
  });
}

// ============================================================================
// ADMIN APIs - Review Sources
// ============================================================================

export interface ReviewSource {
  id: string;
  name: string;
  url: string;
  status: 'available' | 'unavailable';
  lastChecked: string;
  apiLimit: number;
  apiUsed: number;
  avgResponseTime: string;
}

/**
 * Get all review sources
 * FastAPI endpoint: GET /api/admin/sources
 */
export async function getSources(): Promise<ReviewSource[]> {
  return apiRequest<ReviewSource[]>('/api/admin/sources');
}

/**
 * Update review source
 * FastAPI endpoint: PUT /api/admin/sources/{sourceId}
 */
export async function updateSource(sourceId: string, source: Partial<ReviewSource>): Promise<ReviewSource> {
  return apiRequest<ReviewSource>(`/api/admin/sources/${sourceId}`, {
    method: 'PUT',
    body: JSON.stringify(source),
  });
}

/**
 * Check source status
 * FastAPI endpoint: POST /api/admin/sources/{sourceId}/check
 */
export async function checkSourceStatus(sourceId: string): Promise<ReviewSource> {
  return apiRequest<ReviewSource>(`/api/admin/sources/${sourceId}/check`, {
    method: 'POST',
  });
}

export interface SerpApiUsage {
  remaining: number;
  total?: number;
  display?: string; // optional: backend may return remaining-only
}

/**
 * Get shared SerpApi usage from backend
 * FastAPI endpoint: GET /api/serpapi-usage
 */
export async function getSerpApiUsage(): Promise<SerpApiUsage> {
  return apiRequest<SerpApiUsage>('/api/serpapi-usage');
}

// ============================================================================
// HELPER: Token Management (if using JWT)
// ============================================================================

export function setAuthToken(token: string) {
  localStorage.setItem('auth_token', token);
}

export function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

export function removeAuthToken() {
  localStorage.removeItem('auth_token');
}

// Add token to requests automatically
export async function authenticatedRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  
  return apiRequest<T>(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
}
