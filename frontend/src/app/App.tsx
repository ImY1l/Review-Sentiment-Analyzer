import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { UserSearchPage } from './pages/UserSearchPage';
import { UserResultsPage } from './pages/UserResultsPage';
import { AdminLogsPage } from './pages/AdminLogsPage';
import { AdminUsersPage } from './pages/AdminUsersPage';
import { AdminSourcesPage } from './pages/AdminSourcesPage';
import { Moon, Sun, LogOut } from 'lucide-react';

function ProtectedRoute({ children, allowedRole }: { children: React.ReactNode; allowedRole: 'user' | 'admin' }) {
  const { user } = useApp();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== allowedRole) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppContent() {
  const { user, theme, toggleTheme, logout } = useApp();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen">
      {/* Theme Toggle - Show everywhere */}
      <div className="fixed top-4 right-4 flex items-center gap-3 z-50">
        <button
          onClick={toggleTheme}
          className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-lg hover:shadow-xl transition-all border border-gray-200 dark:border-gray-700"
          title="Toggle theme"
        >
          {theme === 'light' ? (
            <Moon className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          ) : (
            <Sun className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          )}
        </button>
        
        {/* Logout - Show only when logged in */}
        {user && (
          <button
            onClick={handleLogout}
            className="px-4 py-3 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg shadow-lg hover:shadow-xl transition-all border border-gray-200 dark:border-gray-700 flex items-center gap-2"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        )}
      </div>

      <Routes>
        {/* Public Routes */}
        <Route path="/" element={user ? (
          user.role === 'admin' ? <Navigate to="/admin/logs" replace /> : <Navigate to="/search" replace />
        ) : <LandingPage />} />
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/register" element={user ? <Navigate to="/" replace /> : <RegisterPage />} />

        {/* User Routes */}
        <Route path="/search" element={
          <ProtectedRoute allowedRole="user">
            <UserSearchPage />
          </ProtectedRoute>
        } />
        <Route path="/results" element={
          <ProtectedRoute allowedRole="user">
            <UserResultsPage />
          </ProtectedRoute>
        } />

        {/* Admin Routes */}
        <Route path="/admin/logs" element={
          <ProtectedRoute allowedRole="admin">
            <AdminLogsPage />
          </ProtectedRoute>
        } />
        <Route path="/admin/users" element={
          <ProtectedRoute allowedRole="admin">
            <AdminUsersPage />
          </ProtectedRoute>
        } />
        <Route path="/admin/sources" element={
          <ProtectedRoute allowedRole="admin">
            <AdminSourcesPage />
          </ProtectedRoute>
        } />

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppContent />
      </AppProvider>
    </BrowserRouter>
  );
}