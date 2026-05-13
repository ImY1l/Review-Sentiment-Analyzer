import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { ChevronDown, ChevronUp, Brain, ArrowLeft, ThumbsUp, ThumbsDown, BarChart3, RefreshCw } from 'lucide-react';
import { Skeleton } from '../../components/ui/skeleton';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const CATEGORY_NAMES: Record<string, string> = {
  'ecommerce': 'E-commerce',
  'food': 'Food & dining',
  'locations': 'Locations',
};

const PLATFORM_NAME_MAP: Record<string, string> = {
  'google_maps': 'Google Maps',
  'tripadvisor': 'Tripadvisor',
  'yelp': 'Yelp',
  'amazon': 'Amazon',
  'shopee': 'Shopee',
  'lazada': 'Lazada',
};


const SENTIMENT_COLORS: Record<string, string> = {
  'Positive': '#10b981',
  'Neutral': '#6b7280',
  'Negative': '#ef4444'
};

export function UserResultsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentProductId, currentCategory } = useApp();
  const productId = searchParams.get('productId') || currentProductId;
  const queryFromUrl = searchParams.get('query') || '';
  const platformsFromUrl = searchParams.get('platforms')?.split(',') || ['lazada'];
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedSection, setExpandedSection] = useState<string | null>('summary');
  const [retryCount, setRetryCount] = useState(0);
  const transformedData = React.useMemo(() => {
    if (!analysisData) return null;

    const rawSentiment = analysisData.sentiment_data || [];
    const sentimentTotal = rawSentiment.reduce((acc: number, s: any) => acc + (Number(s.value) || 0), 0) || 0;

    return {
      summary: analysisData.summary || 'No summary available.',
      pros: analysisData.pros || [],
      cons: analysisData.cons || [],
      // Backend may return counts in sentiment_data.value.
      // Convert to percentages for pie display, but keep the original count for hover.
      sentimentData: rawSentiment.map((item: any) => {
        const count = Number(item.value) || 0;
        const percentage = sentimentTotal > 0 ? (count / sentimentTotal) * 100 : 0;

        return {
          ...item,
          count,
          value: Math.round(percentage * 10) / 10, // keep 1-decimal precision for label
          color: SENTIMENT_COLORS[item.name] || '#8884d8'
        };
      }),
      ratingData: analysisData.rating_data || [],
      avg_rating: analysisData.avg_rating || 0,
      recommend_rate: analysisData.recommend_rate || 0,
      total_reviews: analysisData.total_reviews || 0,
      verified_percentage: analysisData.verified_percentage || 0
    };
  }, [analysisData]);

  // Fetch analysis data
  useEffect(() => {
    const fetchData = async () => {
      if (!productId) {
        setError('No product ID found. Please search again.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError('');

      try {
        const response = await fetch(`http://localhost:8000/api/results/${productId}`, {
          signal: AbortSignal.timeout(30000)
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch analysis: ${response.status}`);
        }

        const data = await response.json();
        setAnalysisData(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [productId, retryCount]);

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    setError('');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950 py-8 px-4">
        <div className="max-w-5xl mx-auto space-y-4">
          <Skeleton className="h-12 w-64" />
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 space-y-4">
            <Skeleton className="h-8 w-80" />
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
          <div className="space-y-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6">
              <Skeleton className="h-12 w-48 mb-4" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4" />
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6">
              <Skeleton className="h-12 w-40 mb-4" />
              <div className="grid md:grid-cols-2 gap-6">
                <Skeleton className="h-64" />
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950 py-8 px-4 flex items-center justify-center">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md text-center shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="w-16 h-16 mx-auto mb-4 text-red-500">
            <BarChart3 className="w-16 h-16" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No Analysis Data</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
          >
            <RefreshCw className="w-4 h-4 animate-spin" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!productId && !queryFromUrl) {
    navigate('/search');
    return null;
  }

  const toggleSection = (section: string) => {
    setExpandedSection(prev => prev === section ? null : section);
  };

  const Section = ({ 
    id, 
    title, 
    icon: Icon, 
    children 
  }: { 
    id: string; 
    title: string; 
    icon: React.ElementType; 
    children: React.ReactNode;
  }) => {
    const isExpanded = expandedSection === id;
    
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden border border-gray-200 dark:border-gray-700">
        <button
          onClick={() => toggleSection(id)}
          className="w-full px-6 py-5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Icon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
          </div>
          {isExpanded ? (
            <ChevronUp className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          ) : (
            <ChevronDown className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          )}
        </button>
        
        {isExpanded && (
          <div className="px-6 py-5 border-t border-gray-200 dark:border-gray-700">
            {children}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/search')}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 mb-4 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Search
          </button>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-2">
              <Brain className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {queryFromUrl || 'Analysis Results'}
              </h1>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Platforms: {platformsFromUrl
                .map((p) => PLATFORM_NAME_MAP[p] || (p ? p.charAt(0).toUpperCase() + p.slice(1) : p))
                .join(', ')}
            </p>
            {currentCategory && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Category: {CATEGORY_NAMES[currentCategory] || currentCategory}
              </p>
            )}
          </div>
        </div>

        {/* Expandable Sections */}
        <div className="space-y-4">
          {/* Summary Section */}
          <Section id="summary" title="Summary" icon={Brain}>
            <div className="prose dark:prose-invert max-w-none">
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                {transformedData?.summary}
              </p>
            </div>
          </Section>

          {/* Pros & Cons Section */}
          <Section id="pros-cons" title="Pros & Cons" icon={ThumbsUp}>
            <div className="grid md:grid-cols-2 gap-6">
              {/* Pros */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-lg">
                    <ThumbsUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Pros</h3>
                </div>
                <ul className="space-y-2">
                  {transformedData?.pros.map((pro: string, index: number) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-green-600 dark:text-green-400 mt-1">•</span>
                      <span className="text-gray-700 dark:text-gray-300">{pro}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Cons */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded-lg">
                    <ThumbsDown className="w-5 h-5 text-red-600 dark:text-red-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Cons</h3>
                </div>
                <ul className="space-y-2">
                  {transformedData?.cons.map((con: string, index: number) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-red-600 dark:text-red-400 mt-1">•</span>
                      <span className="text-gray-700 dark:text-gray-300">{con}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Section>

          {/* Visuals Section */}
          <Section id="visuals" title="Visual Analytics" icon={BarChart3}>
            <div className="space-y-8">
              {/* Sentiment Distribution */}
              <div>
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Sentiment Distribution</h3>
                <div className="grid md:grid-cols-2 gap-6">
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={transformedData?.sentimentData || []}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, value }) => `${name}: ${value}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {(transformedData?.sentimentData || []).map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  
                  <div className="flex flex-col justify-center space-y-3">
                    {(transformedData?.sentimentData || []).map((item: any) => (
                      <div key={item.name} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                        <div className="flex items-center gap-3">
                          <div className="w-4 h-4 rounded" style={{ backgroundColor: item.color }}></div>
                          <span className="font-medium text-gray-900 dark:text-white">{item.name}</span>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold text-gray-900 dark:text-white">{item.value}%</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">{item.count} reviews</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Rating Distribution */}
              <div>
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Rating Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={transformedData?.ratingData || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="rating" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1f2937', 
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="count" fill="#8b5cf6" name="Number of Reviews" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Rating Trend */}
              <div>
                <h3 className="text-lg mb-4 text-gray-900 dark:text-white">Key Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
                    <div className="text-2xl text-blue-600 dark:text-blue-400 mb-1">{transformedData?.avg_rating?.toFixed(1) || '0.0'}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Average Rating</div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4">
                    <div className="text-2xl text-green-600 dark:text-green-400 mb-1">{transformedData?.recommend_rate?.toFixed(0)}%</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Recommend Rate</div>
                  </div>
                  <div className="bg-purple-50 dark:bg-purple-900/30 rounded-lg p-4">
                    <div className="text-2xl text-purple-600 dark:text-purple-400 mb-1">{transformedData?.total_reviews?.toLocaleString() || '0'}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Total Reviews</div>
                  </div>
                  <div className="bg-orange-50 dark:bg-orange-900/30 rounded-lg p-4">
                    <div className="text-2xl text-orange-600 dark:text-orange-400 mb-1">{transformedData?.verified_percentage?.toFixed(0)}%</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Verified Purchases</div>
                  </div>
                </div>
              </div>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
