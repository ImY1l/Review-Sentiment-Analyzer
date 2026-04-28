import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Search, Brain, Clock, Menu, X, ArrowLeft, Tag } from 'lucide-react';
import { unifiedSearch } from '../services/api';

const PLATFORMS = [
  { id: 'lazada', name: 'Lazada', category: 'shopping' },
  { id: 'shopee', name: 'Shopee', category: 'shopping' },
  { id: 'amazon', name: 'Amazon', category: 'shopping' },
  { id: 'google', name: 'Google Reviews', category: 'general' },
];


const CATEGORY_NAMES: Record<string, string> = {
  'tech': 'Tech & Electronics',
  'food': 'Food & Dining',
  'travel': 'Travel & Hotels',
  'fashion': 'Fashion & Apparel',
  'home': 'Home & Garden',
  'beauty': 'Beauty & Personal Care',
  'sports': 'Sports & Fitness',
  'entertainment': 'Entertainment & Media',
  'shopping': 'Shopping & Retail',
  'health': 'Health & Medical',
  'education': 'Education & Learning',
  'automotive': 'Automotive',
  'business': 'Business & Services',
};

export function UserSearchPage() {
  const navigate = useNavigate();
const { user, searchHistory, addSearchHistory, currentCategory, setCurrentProductId } = useApp();
  const [query, setQuery] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['lazada']);
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  // Redirect to category selection if no category is selected
  useEffect(() => {
    if (!currentCategory) {
      navigate('/categories');
    }
  }, [currentCategory, navigate]);

  if (!currentCategory) {
    return null;
  }

  const handlePlatformToggle = (platformId: string) => {
    setSelectedPlatforms(prev => 
      prev.includes(platformId) 
        ? prev.filter(id => id !== platformId)
        : [...prev, platformId]
    );
  };

  const handleSearch = async () => {
    if (isSearching) return;

    setError('');

    if (!query.trim()) {
      setError('Please enter a product name');
      return;
    }

    if (selectedPlatforms.length === 0) {
      setError('Please select at least one review platform');
      return;
    }

    setIsSearching(true);

    try {
      const userId = user?.username || 'anonymous';

      // Filter only supported platforms (lazada, amazon)
      const supportedPlatforms = selectedPlatforms.filter(
        p => p === 'lazada' || p === 'amazon'
      );

      if (supportedPlatforms.length === 0) {
        throw new Error('No supported platforms selected. Please choose Lazada or Amazon.');
      }

      console.log('Starting unified search for:', query, 'on platforms:', supportedPlatforms);

      // Unified search: scrape + analyze in one call
      const result = await unifiedSearch({
        query: query.trim(),
        user_id: userId,
        platforms: supportedPlatforms,
      });

      if (!result.success || !result.product_id) {
        throw new Error(result.message || 'Search failed - no product found');
      }

      console.log('Unified search result:', result);

      // Set context and history
      setCurrentProductId(result.product_id);
      addSearchHistory(query, currentCategory || 'general', supportedPlatforms);

      // Navigate to results
      navigate(`/results?productId=${result.product_id}&platforms=${supportedPlatforms.join(',')}&query=${encodeURIComponent(query.trim())}`);

    } catch (err: any) {
      console.error('Search failed:', err);
      setError(err.message || 'Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleHistoryClick = (historyItem: typeof searchHistory[0]) => {
    setQuery(historyItem.query);
    setSelectedPlatforms(historyItem.platforms);
    setIsSidebarOpen(false); // Close sidebar after selecting
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950">
      <div className="flex flex-col min-h-screen relative">
        {/* Sidebar Toggle Button */}
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="fixed top-20 left-4 z-50 p-3 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title={isSidebarOpen ? "Close history" : "Open history"}
        >
          {isSidebarOpen ? (
            <X className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          ) : (
            <Menu className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          )}
        </button>

        {/* Sidebar - Search History */}
        <div 
          className={`
            w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-6
            fixed top-0 left-0 h-full z-40 transition-transform duration-300 ease-in-out
            ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          `}
        >
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Search History</h2>
            </div>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="Close"
            >
              <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
          </div>

          {searchHistory.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No recent searches</p>
          ) : (
            <div className="space-y-3">
              {searchHistory.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleHistoryClick(item)}
                  className="w-full text-left p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-purple-50 dark:hover:bg-purple-900/20 border border-gray-200 dark:border-gray-600 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Tag className="w-3 h-3 text-purple-600 dark:text-purple-400" />
                    <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                      {CATEGORY_NAMES[item.category] || item.category}
                    </span>
                  </div>
                  <p className="font-medium text-gray-900 dark:text-white truncate">{item.query}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {item.platforms.join(', ')}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    {new Date(item.date).toLocaleDateString()}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Loading Overlay */}
        {isSearching && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl border border-gray-200 dark:border-gray-700">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center animate-spin">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Analyzing Reviews</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-2">
                Scraping from: <span className="font-semibold text-purple-600 dark:text-purple-400">{selectedPlatforms.filter(p => p === 'lazada' || p === 'amazon').join(', ')}</span>
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm mb-4">This may take 2-5 minutes</p>
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}} />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}} />
              </div>
            </div>
          </div>
        )}

        {/* Overlay for mobile/tablet */}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-30"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <div className={`flex-1 p-6 lg:p-12 ${isSearching ? 'opacity-50 pointer-events-none' : ''}`}>
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
              <div className="flex items-center justify-center gap-3 mb-4">
                <div className="bg-gradient-to-br from-purple-600 to-blue-600 p-3 rounded-xl shadow-lg">
                  <Brain className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                  Review Sentiment Analyzer
                </h1>
              </div>
              <p className="text-xl text-gray-700 dark:text-gray-300">
                Welcome, {user?.name || user?.username}!
              </p>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                Search for any product to analyze reviews from across the internet
              </p>
            </div>

            {/* Search Bar */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 space-y-6">
              {/* Category Badge with Back Button */}
              {currentCategory && (
                <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2">
                    <Tag className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">Category:</span>
                    <span className="font-semibold text-purple-600 dark:text-purple-400">
                      {CATEGORY_NAMES[currentCategory] || currentCategory}
                    </span>
                  </div>
                  <button
                    onClick={() => navigate('/categories')}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Change Category
                  </button>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-3 text-gray-700 dark:text-gray-300">
                  What product would you like to analyze?
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    className="w-full px-6 py-4 pr-12 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
                    placeholder='e.g., "iPhone 15 Pro" or "Airbnb Paris"'
                  />
                  <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-6 h-6 text-gray-400" />
                </div>
              </div>


              {/* Platform Selection */}
              <div>
                <label className="block text-sm font-medium mb-3 text-gray-700 dark:text-gray-300">
                  Select review platforms
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {PLATFORMS.map((platform) => (
                    <label
                      key={platform.id}
                      className="flex items-center gap-3 p-4 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-600 cursor-pointer transition-colors bg-gray-50 dark:bg-gray-700/50"
                    >
                      <input
                        type="checkbox"
                        checked={selectedPlatforms.includes(platform.id)}
                        onChange={() => handlePlatformToggle(platform.id)}
                        className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <span className="text-gray-900 dark:text-white font-medium">{platform.name}</span>
                    </label>
                  ))}
                </div>
              </div>


              {/* Error Message */}
              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400">
                  {error}
                </div>
              )}

              {/* Search Button */}
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200 font-semibold text-lg flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed disabled:scale-100"
              >
                {isSearching ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analyzing Reviews...
                  </>
                ) : (
                  <>
                    <Search className="w-5 h-5" />
                    Analyze Reviews
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}