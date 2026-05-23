import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, Users, Database, AlertTriangle, CheckCircle } from 'lucide-react';
import { checkSourceStatus, getSerpApiUsage, getSources, ReviewSource, updateSource } from '../services/api';

export function AdminSourcesPage() {
  const SERPAPI_PLATFORMS = useMemo(() => new Set(['amazon', 'google', 'tripadvisor', 'yelp']), []);
  const SERPAPI_MONTHLY_LIMIT_FALLBACK = 250;

  const navigate = useNavigate();
  const [sources, setSources] = useState<ReviewSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [serpUsage, setSerpUsage] = useState<{ remaining: number } | null>(null);

  useEffect(() => {
    async function fetchSources() {
      try {
        setLoading(true);
        setError('');

        try {
          const usage = await getSerpApiUsage();
          setSerpUsage({ remaining: usage.remaining ?? 0 });
        } catch (e) {
          console.error('Failed to fetch SerpApi usage:', e);
          setSerpUsage(null);
        }

        const data = await getSources();
        setSources(data);
      } catch (e) {
        console.error('Failed to fetch sources:', e);
        setError('Failed to load review sources.');
      } finally {
        setLoading(false);
      }
    }

    fetchSources();
  }, []);

  const sortedSources = useMemo(() => sources, [sources]);

  const toggleStatus = async (sourceId: string) => {
    const current = sources.find((s) => s.id === sourceId);
    if (!current) return;

    const nextStatus = current.status === 'available' ? 'unavailable' : 'available';

    try {
      const updated = await updateSource(sourceId, { status: nextStatus });
      setSources((prev) => prev.map((s) => (s.id === sourceId ? updated : s)));
    } catch (e) {
      console.error('Failed to toggle source status:', e);
    }
  };

  const handleCheck = async (sourceId: string) => {
    try {
      const updated = await checkSourceStatus(sourceId);
      setSources((prev) => prev.map((s) => (s.id === sourceId ? updated : s)));
    } catch (e) {
      console.error('Failed to check source status:', e);
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === 'available') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
          <CheckCircle className="w-3 h-3" />
          Available
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">
        <AlertTriangle className="w-3 h-3" />
        Unavailable
      </span>
    );
  };

  const getUsageColor = (used: number, limit: number) => {
    if (!limit) return 'text-gray-600 dark:text-gray-400';
    const percentage = (used / limit) * 100;
    if (percentage >= 90) return 'text-red-600 dark:text-red-400';
    if (percentage >= 70) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
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
              <p className="text-gray-600 dark:text-gray-400">Manage Review Sources</p>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => navigate('/admin/logs')}
              className="px-4 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg font-medium shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
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
              className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium shadow-md flex items-center gap-2"
            >
              <Database className="w-4 h-4" />
              Review Sources
            </button>
          </div>
        </div>

        {/* Sources Grid */}
        {loading ? (
          <div className="text-gray-700 dark:text-gray-300">Loading sources...</div>
        ) : error ? (
          <div className="text-red-600 dark:text-red-400">{error}</div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {sources.map((source) => (
              <div 
                key={source.id} 
                className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                    {source.name
                      ? source.name.charAt(0).toUpperCase() + source.name.slice(1)
                      : ''}
                  </h3>
                  {getStatusBadge(source.status)}
                </div>
              </div>

              <>
                  {/* Info */}
                  <div className="space-y-3 mb-4">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">API Endpoint</p>
                      <p className="text-xs text-gray-700 dark:text-gray-300 font-mono break-all">
                        {source.url}
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">API Usage</p>
                        {SERPAPI_PLATFORMS.has(source.name.toLowerCase()) ? (
                          (() => {
                            const remaining = serpUsage?.remaining ?? 0;
                            const used = Math.max(SERPAPI_MONTHLY_LIMIT_FALLBACK - remaining, 0);
                            const ratioColor = getUsageColor(used, SERPAPI_MONTHLY_LIMIT_FALLBACK);
                            return (
                              <p className={`text-sm font-semibold ${ratioColor}`}>
                                {serpUsage ? `${used}/${SERPAPI_MONTHLY_LIMIT_FALLBACK}` : 'Loading...'}
                              </p>
                            );
                          })()
                        ) : source.name.toLowerCase() === 'lazada' || source.name.toLowerCase() === 'shopee' ? (
                          <p className="text-sm font-semibold text-green-600 dark:text-green-400">
                            ∞ / ∞
                          </p>
                        ) : (
                          <p className={`text-sm font-semibold ${getUsageColor(source.apiUsed, source.apiLimit)}`}>
                            {source.apiUsed} / {source.apiLimit}
                          </p>
                        )}
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Response</p>
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {source.avgResponseTime}
                        </p>
                      </div>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Last Checked</p>
                      <p className="text-xs text-gray-700 dark:text-gray-300">
                        {source.lastChecked}
                      </p>
                    </div>

                    {/* Usage Bar */}
                    <div>
                      {SERPAPI_PLATFORMS.has(source.name.toLowerCase()) ? (
                        <>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full transition-all ${
                                  (() => {
                                    const used = Math.max(SERPAPI_MONTHLY_LIMIT_FALLBACK - (serpUsage?.remaining ?? 0), 0);
                                    const ratio = used / SERPAPI_MONTHLY_LIMIT_FALLBACK;
                                    if (ratio >= 0.9) return 'bg-red-500';
                                    if (ratio >= 0.7) return 'bg-yellow-500';
                                    return 'bg-green-500';
                                  })()
                                }`}
                                style={{
                                  width: serpUsage
                                    ? `${(Math.max(SERPAPI_MONTHLY_LIMIT_FALLBACK - (serpUsage?.remaining ?? 0), 0) / SERPAPI_MONTHLY_LIMIT_FALLBACK) * 100}%`
                                    : '0%',
                                }}
                              />
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {serpUsage
                              ? `${Math.round((serpUsage.remaining / SERPAPI_MONTHLY_LIMIT_FALLBACK) * 100)}% remaining`
                              : 'Loading...'}
                          </p>
                        </>
                      ) : source.name.toLowerCase() === 'lazada' || source.name.toLowerCase() === 'shopee' ? (
                        <>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                            <div className="h-2 rounded-full transition-all bg-green-500" style={{ width: '100%' }} />
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            ∞ remaining
                          </p>
                        </>
                      ) : (
                        <>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                (source.apiUsed / source.apiLimit) >= 0.9 ? 'bg-red-500' :
                                (source.apiUsed / source.apiLimit) >= 0.7 ? 'bg-yellow-500' :
                                'bg-green-500'
                              }`}
                              style={{ width: `${(source.apiUsed / source.apiLimit) * 100}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {Math.round((source.apiUsed / source.apiLimit) * 100)}% used
                          </p>
                        </>
                      )}
                    </div>
                  </div>
              </>

              {/* Toggle Button + Check */}
              <div className="flex gap-2">
                <button
                  onClick={() => toggleStatus(source.id)}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                    source.status === 'available'
                      ? 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/40'
                      : 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/40'
                  }`}
                >
                  Mark as {source.status === 'available' ? 'Unavailable' : 'Available'}
                </button>
                <button
                  onClick={() => handleCheck(source.id)}
                  className="px-4 py-2 rounded-lg font-medium bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  title="Check source status"
                >
                  Check
                </button>
              </div>
            </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
