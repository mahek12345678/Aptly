import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserProfile {
  id?: string;
  google_id?: string | null;
  email: string;
  name: string;
  picture?: string | null;
  profile_picture_url?: string | null;
  onboarding_completed: boolean;
  onboarding_step: number;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (googleCredential: string) => Promise<UserProfile>;
  signup: (googleCredential: string) => Promise<UserProfile>;
  updateOnboardingProgress: (step?: number, completed?: boolean) => Promise<UserProfile>;
  refreshUser: () => Promise<UserProfile | null>;
  logout: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthState | undefined>(undefined);

const TOKEN_KEY = 'aptly_token';
const USER_KEY = 'aptly_user';

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const stored = localStorage.getItem(USER_KEY);
      return stored ? (JSON.parse(stored) as UserProfile) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );

  const [isLoading, setIsLoading] = useState(false);

  const refreshUser = useCallback(async (): Promise<UserProfile | null> => {
    try {
      const profile = await api.get<UserProfile>('/api/auth/me');
      setUser(profile);
      localStorage.setItem(USER_KEY, JSON.stringify(profile));
      return profile;
    } catch {
      setUser(null);
      setToken(null);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      return null;
    }
  }, []);

  // Validate stored token on mount
  useEffect(() => {
    if (!token) return;
    setIsLoading(true);
    refreshUser().finally(() => setIsLoading(false));
  }, [token, refreshUser]);

  const login = useCallback(async (googleCredential: string): Promise<UserProfile> => {
    setIsLoading(true);
    try {
      const response = await api.post<TokenResponse>('/api/auth/google/login', {
        credential: googleCredential,
      });
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem(TOKEN_KEY, response.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(response.user));
      return response.user;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signup = useCallback(async (googleCredential: string): Promise<UserProfile> => {
    setIsLoading(true);
    try {
      const response = await api.post<TokenResponse>('/api/auth/google/signup', {
        credential: googleCredential,
      });
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem(TOKEN_KEY, response.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(response.user));
      return response.user;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateOnboardingProgress = useCallback(
    async (step?: number, completed?: boolean): Promise<UserProfile> => {
      const updated = await api.put<UserProfile>('/api/onboarding/step', {
        step,
        completed,
      });
      setUser(updated);
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      return updated;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.post('/api/auth/logout');
    } catch {
      // Ignore — logout always clears local state
    } finally {
      setUser(null);
      setToken(null);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      token,
      isAuthenticated: !!token && !!user,
      isLoading,
      login,
      signup,
      updateOnboardingProgress,
      refreshUser,
      logout,
    }),
    [user, token, isLoading, login, signup, updateOnboardingProgress, refreshUser, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}
