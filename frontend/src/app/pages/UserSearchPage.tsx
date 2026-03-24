import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Search, Brain, Clock, Menu, X } from 'lucide-react';

const PLATFORMS = [
  { id: 'amazon', name: 'Amazon', category: 'shopping' },
  { id: 'yelp', name: 'Yelp', category: 'restaurant' },
  { id: 'tripadvisor', name: 'TripAdvisor', category: 'travel' },
  { id: 'google', name: 'Google Reviews', category: 'general' },
];

export function UserSearchPage() {
  const navigate = useNavigate();
  const { user, searchHistory, addSearchHistory } = useApp();
  const [query, setQuery] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['amazon', 'google']);
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handlePlatformToggle = (platformId: string) => {
    setSelectedPlatforms(prev => 
      prev.includes(platformId) 
        ? prev.filter(id => id !== platformId)
        : [...prev, platformId]
    );
  };

  const handleSearch = () => {
    setError('');

    if (!query.trim()) {
      setError('Please enter a product name');
      return;
    }

    if (selectedPlatforms.length === 0) {
      setError('Please select at least one review platform');
      return;
    }

    // Mock search logic
    const lowerQuery = query.toLowerCase().trim();

    // Case 1: Too ambiguous (just "iphone")
    if (lowerQuery === 'iphone') {
      setError('Your search is too ambiguous. Please specify a model (e.g., "iPhone 15")');
      return;
    }

    // Case 2: Product with incompatible platforms
    if (lowerQuery.includes('iphone') && selectedPlatforms.includes('yelp') && selectedPlatforms.length === 1) {
      setError('No reviews found on the selected platforms. Try selecting different platforms.');
      return;
    }

    // Add to search history and navigate to results
    addSearchHistory(query, selectedPlatforms);
    navigate('/results', { state: { query, platforms: selectedPlatforms } });
  };

  const handleHistoryClick = (historyItem: typeof searchHistory[0]) => {
    setQuery(historyItem.query);
    setSelectedPlatforms(historyItem.platforms);
    setIsSidebarOpen(false); // Close sidebar after selecting
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950">
      <div className="flex flex-col lg:flex-row min-h-screen relative">
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
            lg:w-80 bg-white dark:bg-gray-800 border-b lg:border-r border-gray-200 dark:border-gray-700 p-6
            fixed lg:static top-0 left-0 h-full z-40 transition-transform duration-300 ease-in-out
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

        {/* Overlay for mobile/tablet */}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-30"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <div className="flex-1 p-6 lg:p-12">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
              <div className="flex  flex-col items-center justify-center gap-3 mb-4">
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
                  Select review platforms to scrape
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
                className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200 font-semibold text-lg flex items-center justify-center gap-2"
              >
                <Search className="w-5 h-5" />
                Analyze Reviews
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}