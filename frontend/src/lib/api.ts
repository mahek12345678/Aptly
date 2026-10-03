/**
 * Aptly API client – lightweight fetch wrapper.
 * Injects the Authorization header when a token is present in localStorage.
 */

const BASE_URL = ((import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000').replace(/\/+$/, '');

function formatUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${BASE_URL}${cleanPath}`;
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = localStorage.getItem('aptly_token');
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Prevent browser caching for API requests
  headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';
  headers['Pragma'] = 'no-cache';
  headers['Expires'] = '0';

  const response = await fetch(formatUrl(path), {
    cache: 'no-store',
    ...options,
    headers,
    body:
      options.body !== undefined
        ? isFormData
          ? (options.body as FormData)
          : JSON.stringify(options.body)
        : undefined,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData?.detail ?? `HTTP ${response.status}`);
  }

  // 204 No Content → return undefined cast to T
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body: formData }),
  postBlob: async (path: string, body?: unknown, options?: RequestOptions): Promise<Blob> => {
    const token = localStorage.getItem('aptly_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      ...(options?.headers as Record<string, string>),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(formatUrl(path), {
      cache: 'no-store',
      ...options,
      method: 'POST',
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      const error = new Error(errorData?.detail ?? `HTTP ${response.status}`) as Error & { status?: number };
      error.status = response.status;
      throw error;
    }
    return response.blob();
  },
  getBlob: async (path: string, options?: RequestOptions): Promise<Blob> => {
    const token = localStorage.getItem('aptly_token');
    const headers: Record<string, string> = {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      ...(options?.headers as Record<string, string>),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const { body: _ignored, ...restOptions } = options || {};
    // Add cache-busting timestamp parameter so browser HTTP cache NEVER serves stale file bytes
    const separator = path.includes('?') ? '&' : '?';
    const cacheBustedPath = `${path}${separator}_t=${Date.now()}`;
    const response = await fetch(formatUrl(cacheBustedPath), {
      cache: 'no-store',
      ...restOptions,
      method: 'GET',
      headers,
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      const error = new Error(errorData?.detail ?? `HTTP ${response.status}`) as Error & { status?: number };
      error.status = response.status;
      throw error;
    }
    return response.blob();
  },
};

