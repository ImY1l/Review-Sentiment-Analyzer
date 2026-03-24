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
  platforms: string[];
  date: string;
}

interface AppContextType {
  user: User | null;
  theme: 'light' | 'dark';
  searchHistory: SearchHistory[];
  login: (username: string, password: string) => boolean;
  logout: () => void;
  register: (data: { name: string; email: string; username: string; password: string }) => boolean;
  toggleTheme: () => void;
  addSearchHistory: (query: string, platforms: string[]) => void;
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

  useEffect(() => {
    // Apply theme to document
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const login = (username: string, password: string): boolean => {
    // Check admin
    if (username === MOCK_ADMIN.username && password === MOCK_ADMIN.password) {
      setUser({ username, role: 'admin' });
      return true;
    }

    // Check users
    const foundUser = MOCK_USERS.find(u => u.username === username && u.password === password);
    if (foundUser) {
      setUser({ username, name: foundUser.name, email: foundUser.email, role: 'user' });
      return true;
    }

    return false;
  };

  const logout = () => {
    setUser(null);
    setSearchHistory([]);
  };

  const register = (data: { name: string; email: string; username: string; password: string }): boolean => {
    // Check if username already exists
    if (MOCK_USERS.find(u => u.username === data.username) || data.username === MOCK_ADMIN.username) {
      return false;
    }

    // Add to mock database
    MOCK_USERS.push({ ...data, role: 'user' });
    return true;
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const addSearchHistory = (query: string, platforms: string[]) => {
    const newSearch: SearchHistory = {
      id: Date.now().toString(),
      query,
      platforms,
      date: new Date().toISOString()
    };

    setSearchHistory(prev => [newSearch, ...prev].slice(0, 3)); // Keep only last 3
  };

  return (
    <AppContext.Provider value={{ user, theme, searchHistory, login, logout, register, toggleTheme, addSearchHistory }}>
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
