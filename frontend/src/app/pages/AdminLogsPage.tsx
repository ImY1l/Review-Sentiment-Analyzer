import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle, XCircle, Info, Brain, Users, Database } from 'lucide-react';
import { getLogs } from '../services/api';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'error' | 'warning' | 'info' | 'success';
  action?: string;
  message: string;
  details: string;
  user?: string;
}

export function AdminLogsPage() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterLevel, setFilterLevel] = useState<string>('all');

  useEffect(() => {
    async function fetchLogs() {
      try {
        setLoading(true);
        setError('');
        const data = await getLogs({ level: filterLevel });
        // Backend may return action/details/message; normalize for UI
        const normalized: LogEntry[] = (data as any[]).map((log) => ({
          id: String(log.id ?? ''),
          timestamp: String(log.timestamp ?? ''),
          level: log.level,
          action: log.action,
          message: String(log.message ?? log.action ?? log.details ?? ''),
          details: String(log.details ?? ''),
          user: log.user ? String(log.user) : undefined,
        }));
        setLogs(normalized);
      } catch (e) {
        console.error(e);
        setError('Failed to load logs.');
      } finally {
        setLoading(false);
      }
    }

    fetchLogs();
  }, [filterLevel]);

  const filteredLogs = filterLevel === 'all' ? logs : logs.filter((log) => log.level === filterLevel);

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'info':
        return <Info className="w-5 h-5 text-blue-500" />;
      default:
        return null;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
      case 'success':
        return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
      case 'info':
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      default:
        return 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-gradient-to-br from-purple-600 to-blue-600 p-3 rounded-xl shadow-lg">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
              <p className="text-gray-600 dark:text-gray-400">System Logs & Errors</p>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => navigate('/admin/logs')}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium shadow-md"
            >
              System Logs
            </button>
            <button
              onClick={() => navigate('/admin/users')}
              className="px-4 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg font-medium shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
            >
              <Users className="w-4 h-4" />
              Manage Users
            </button>
            <button
              onClick={() => navigate('/admin/sources')}
              className="px-4 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg font-medium shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
            >
              <Database className="w-4 h-4" />
              Review Sources
            </button>
          </div>
        </div>

        {/* Filter */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-6">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-medium text-gray-700 dark:text-gray-300">Filter by level:</span>
            {['all', 'error', 'warning', 'success', 'info'].map((level) => (
              <button
                key={level}
                onClick={() => setFilterLevel(level)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  filterLevel === level
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Loading/Error */}
        {loading && (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">Loading logs...</div>
        )}
        {!loading && error && (
          <div className="text-center py-12 text-red-500 dark:text-red-400">{error}</div>
        )}

        {/* Logs Table */}
        {!loading && !error && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Level</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Timestamp</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Message</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredLogs.map((log) => (
                    <tr
                      key={log.id}
                      className={`${getLevelColor(log.level)} hover:opacity-90 transition-opacity`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {getLevelIcon(log.level)}
                          <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                            {log.level}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {log.timestamp}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">{log.message}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{log.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && !error && filteredLogs.length === 0 && (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">No logs found for the selected filter.</div>
        )}
      </div>
    </div>
  );
}

