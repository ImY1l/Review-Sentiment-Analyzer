import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Search, Brain, ArrowLeft, Tag } from 'lucide-react';
import { unifiedSearch, getSources } from '../services/api';

const PLATFORMS = [
  { id: 'lazada', name: 'Lazada', category: 'ecommerce' },
  { id: 'shopee', name: 'Shopee', category: 'ecommerce' },
  { id: 'amazon', name: 'Amazon', category: 'ecommerce' },
  { id: 'google_maps', name: 'Google Maps', category: 'locations', google_type: 'maps' },
  { id: 'yelp', name: 'Yelp', category: 'food' },
  { id: 'tripadvisor', name: 'Tripadvisor', category: 'food' },
];

const CATEGORY_NAMES: Record<string, string> = {
  ecommerce: 'E-commerce',
  food: 'Food & dining',
  locations: 'Locations',
};

export function UserSearchPage() {
  const navigate = useNavigate();
  const { user, searchHistory, addSearchHistory, currentCategory, setCurrentProductId } = useApp();

  const [query, setQuery] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);

  const [error, setError] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const [platformAvailability, setPlatformAvailability] = useState<
    Record<string, 'available' | 'unavailable'>
  >({});
  const [sourcesLoading, setSourcesLoading] = useState(true);

  const platformMap: Record<string, string[]> = {
    ecommerce: ['shopee', 'lazada', 'amazon'],
    food: ['yelp', 'tripadvisor', 'google_maps'],
    locations: ['google_maps', 'yelp', 'tripadvisor'],
  };

  const categoryPlatforms = platformMap[currentCategory || 'ecommerce'] || [];

  // Load platform availability status (from admin sources)
  useEffect(() => {
    let cancelled = false;

    async function loadStatuses() {
      try {
        setSourcesLoading(true);
        const data = await getSources();
        if (cancelled) return;

        const availabilityMap: Record<string, 'available' | 'unavailable'> = {};
        for (const s of data) {
          availabilityMap[s.name.toLowerCase()] = s.status;
        }

        setPlatformAvailability(availabilityMap);

        // Drop any selected platforms that became unavailable.
        setSelectedPlatforms((prev) => prev.filter((p) => availabilityMap[p.toLowerCase()] !== 'unavailable'));
      } catch (e) {
        console.error('Failed to load platform statuses:', e);
      } finally {
        if (!cancelled) setSourcesLoading(false);
      }
    }

    loadStatuses();

    return () => {
      cancelled = true;
    };
  }, []);

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
    const availability = platformAvailability[platformId];

    if (availability && availability !== 'available') return;

    setSelectedPlatforms((prev) =>
      prev.includes(platformId) ? prev.filter((id) => id !== platformId) : [...prev, platformId]
    );
  };

  const handleSearch = async () => {
    if (isSearching) return;

    setError('');

    if (!query.trim()) {
      setError(
        currentCategory === 'food'
          ? 'Please enter a restaurant or food place name'
          : currentCategory === 'locations'
            ? 'Please enter a location name'
            : 'Please enter a product name'
      );
      return;
    }

    if (selectedPlatforms.length === 0) {
      setError('Please select at least one review platform');
      return;
    }

    setIsSearching(true);

    try {
      const userId = user?.username || 'anonymous';

      // Filter platforms: category + available only
      const selectedSupported = selectedPlatforms.filter(
        (p) => categoryPlatforms.includes(p) && platformAvailability[p.toLowerCase()] !== 'unavailable'
      );

      if (selectedSupported.length === 0) {
        throw new Error(`No available platforms for ${CATEGORY_NAMES[currentCategory] || currentCategory}`);
      }

      const supportedPlatforms = selectedSupported;

      const result = await unifiedSearch({
        query: query.trim(),
        user_id: userId,
        platforms: supportedPlatforms,
      });

      if (!result.success || !result.product_id) {
        throw new Error(result.message || 'Search failed - no product found');
      }

      // Set context and history
      setCurrentProductId(result.product_id);
      addSearchHistory(query, currentCategory || 'general', supportedPlatforms);

      // Navigate to results
      navigate(
        `/results?productId=${result.product_id}&platforms=${supportedPlatforms.join(',')}&query=${encodeURIComponent(
          query.trim()
        )}`
      );
    } catch (err: any) {
      console.error('Search failed:', err);
      setError(err.message || 'Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950">
      <div className="flex flex-col min-h-screen relative">
        {/* Loading Overlay */}
        {isSearching && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl border border-gray-200 dark:border-gray-700">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center animate-spin">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Analyzing Reviews</h3>

              <p className="text-gray-600 dark:text-gray-400 mb-2">
                Scraping from:{' '}
                <span className="font-semibold text-purple-600 dark:text-purple-400">
                  {selectedPlatforms
                    .map((id) => {
                      const p = PLATFORMS.find((platform) => platform.id === id);
                      return p ? p.name : id;
                    })
                    .join(', ')}
                </span>
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm mb-4">This may take 2-5 minutes</p>
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
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
              <p className="text-xl text-gray-700 dark:text-gray-300">Welcome, {user?.name || user?.username}!</p>
              <p className="text-gray-600 dark:text-gray-400 mt-2">Search for any product to analyze reviews from across the internet</p>
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
                  {currentCategory === 'food'
                    ? 'What food place would you like to analyze?'
                    : currentCategory === 'locations'
                      ? 'What location would you like to analyze?'
                      : 'What product would you like to analyze?'}
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    className="w-full px-6 py-4 pr-12 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
                    placeholder={
                      currentCategory === 'food'
                        ? 'e.g., "Pizza Hut" or "Starbucks Penang"'
                        : currentCategory === 'locations'
                          ? 'e.g., "Central Park" or "Petronas Twin Towers"'
                          : 'e.g., "iPhone 15 Pro" or "Airbnb Paris"'
                    }
                  />
                  <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-6 h-6 text-gray-400" />
                </div>
              </div>

              {/* Platform Selection */}
              <div>
                <label className="block text-sm font-medium mb-3 text-gray-700 dark:text-gray-300">Select review platforms</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {categoryPlatforms.map((platformId) => {
                    const platform = PLATFORMS.find((p) => p.id === platformId);
                    if (!platform) return null;

                    const availability = platformAvailability[platform.id];
                    const disabled = availability === 'unavailable' || sourcesLoading;

                    return (
                      <label
                        key={platform.id}
                        className="flex items-center gap-3 p-4 rounded-lg border-2 border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-600 cursor-pointer transition-colors bg-gray-50 dark:bg-gray-700/50"
                      >
                        <input
                          type="checkbox"
                          checked={selectedPlatforms.includes(platform.id)}
                          onChange={() => handlePlatformToggle(platform.id)}
                          disabled={disabled}
                          className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
                        />
                        <span className={`font-medium ${disabled ? 'text-gray-400' : 'text-gray-900 dark:text-white'}`}>{platform.name}</span>
                      </label>
                    );
                  })}
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

