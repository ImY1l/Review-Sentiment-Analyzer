import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  username: string;
  name?: string;
  email?: string;
  role: 'user' | 'admin';
}

interface SearchHistory {
  id: string;
  query: string;
  category: string;
  platforms: string[];
  date: string;
}

interface AppContextType {
  user: User | null;
  theme: 'light' | 'dark';
  searchHistory: SearchHistory[];
  currentCategory: string | null;
  currentProductId: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  register: (data: { name: string; email: string; username: string; password: string }) => Promise<boolean>;
  toggleTheme: () => void;
  addSearchHistory: (query: string, category: string, platforms: string[]) => void;
  setCategory: (category: string) => void;
  setCurrentProductId: (productId: string | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// Mock users database
const MOCK_ADMIN = { username: 'ImYous', password: 'Ym__006', role: 'admin' as const };
const MOCK_USERS: Array<{ username: string; password: string; name: string; email: string; role: 'user' }> = [
  { username: 'demo', password: 'Demo@123', name: 'Demo User', email: 'demo@example.com', role: 'user' }
];

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
const [currentCategory, setCurrentCategory] = useState<string | null>(null);
  const [currentProductId, setCurrentProductId] = useState<string | null>(null);

  useEffect(() => {
    // Apply theme to document
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const login = async (username: string, password: string): Promise<boolean> => {
    const url = 'http://localhost:8000/api/auth/login';
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result?.success === false) {
        return false;
      }

      if (!result?.username || !result?.role) {
        return false;
      }

      setUser({
        username: result.username,
        name: result.name,
        email: result.email,
        role: result.role
      });
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };


  const logout = () => {
    setUser(null);
    setSearchHistory([]);
  };

  const register = async (data: { name: string; email: string; username: string; password: string }): Promise<boolean> => {
    const url = 'http://localhost:8000/api/auth/register';
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      const result = await response.json();
      return result.success;
    } catch (error) {
      console.error('Registration failed:', error);
      return false;
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const addSearchHistory = (query: string, category: string, platforms: string[]) => {
    const newSearch: SearchHistory = {
      id: Date.now().toString(),
      query,
      category,
      platforms,
      date: new Date().toISOString()
    };

    setSearchHistory(prev => [newSearch, ...prev].slice(0, 3)); // Keep only last 3
  };

const setCategory = (category: string) => {
    setCurrentCategory(category);
  };

  const setCurrentProductIdLocal = (productId: string | null) => {
    setCurrentProductId(productId);
  };

  return (
    <AppContext.Provider value={{ user, theme, searchHistory, currentCategory, currentProductId, login, logout, register, toggleTheme, addSearchHistory, setCategory, setCurrentProductId: setCurrentProductIdLocal }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}
