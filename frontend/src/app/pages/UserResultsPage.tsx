import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Brain, ArrowLeft, ThumbsUp, ThumbsDown, BarChart3 } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

interface LocationState {
  query: string;
  category?: string;
  platforms: string[];
}

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

// Mock data generator
const generateMockData = (query: string) => {
  return {
    summary: `Based on analysis of over 2,500 reviews for ${query}, the product demonstrates strong market performance with an average rating of 4.3 out of 5 stars. Customer satisfaction is particularly high in areas of build quality and performance, though some concerns have been raised about price value. The sentiment analysis reveals predominantly positive reception, with 72% of reviewers recommending the product. The device excels in its core functionality and user experience, making it a competitive option in its category. Recent reviews show improving customer sentiment following software updates.`,
    
    pros: [
      'Exceptional build quality and premium materials',
      'Outstanding performance for demanding tasks',
      'Long battery life exceeding expectations',
      'Intuitive and user-friendly interface',
      'Regular software updates and support',
      'Excellent camera system with advanced features',
      'Fast charging capabilities',
      'Strong ecosystem integration'
    ],
    
    cons: [
      'Premium pricing compared to competitors',
      'Limited storage in base model',
      'No expandable storage option',
      'Occasional heating during intensive use',
      'Accessories sold separately at high prices',
      'Learning curve for advanced features',
      'Limited customization options'
    ],
    
    sentimentData: [
      { name: 'Positive', value: 72, color: '#10b981' },
      { name: 'Neutral', value: 18, color: '#6b7280' },
      { name: 'Negative', value: 10, color: '#ef4444' }
    ],
    
    ratingData: [
      { rating: '5 Stars', count: 1250, percentage: 50 },
      { rating: '4 Stars', count: 625, percentage: 25 },
      { rating: '3 Stars', count: 375, percentage: 15 },
      { rating: '2 Stars', count: 150, percentage: 6 },
      { rating: '1 Star', count: 100, percentage: 4 }
    ],
    
    trendData: [
      { month: 'Sep', rating: 4.1 },
      { month: 'Oct', rating: 4.2 },
      { month: 'Nov', rating: 4.2 },
      { month: 'Dec', rating: 4.3 },
      { month: 'Jan', rating: 4.4 },
      { month: 'Feb', rating: 4.3 }
    ]
  };
};

export function UserResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState;
  
  const [expandedSection, setExpandedSection] = useState<string | null>('summary');

  if (!state?.query) {
    navigate('/search');
    return null;
  }

  const data = generateMockData(state.query);

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
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analysis Results</h1>
            </div>
            <p className="text-lg text-gray-600 dark:text-gray-300">
              Product: <span className="font-semibold text-gray-900 dark:text-white">{state.query}</span>
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Platforms: {state.platforms.join(', ')}
            </p>
            {state.category && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Category: {CATEGORY_NAMES[state.category] || state.category}
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
                {data.summary}
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
                  {data.pros.map((pro, index) => (
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
                  {data.cons.map((con, index) => (
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
                        data={data.sentimentData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, value }) => `${name}: ${value}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {data.sentimentData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  
                  <div className="flex flex-col justify-center space-y-3">
                    {data.sentimentData.map((item) => (
                      <div key={item.name} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                        <div className="flex items-center gap-3">
                          <div className="w-4 h-4 rounded" style={{ backgroundColor: item.color }}></div>
                          <span className="font-medium text-gray-900 dark:text-white">{item.name}</span>
                        </div>
                        <span className="font-semibold text-gray-900 dark:text-white">{item.value}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Rating Distribution */}
              <div>
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Rating Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.ratingData}>
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
                    <div className="text-2xl text-blue-600 dark:text-blue-400 mb-1">4.3</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Average Rating</div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4">
                    <div className="text-2xl text-green-600 dark:text-green-400 mb-1">87%</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Recommend Rate</div>
                  </div>
                  <div className="bg-purple-50 dark:bg-purple-900/30 rounded-lg p-4">
                    <div className="text-2xl text-purple-600 dark:text-purple-400 mb-1">2,500</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Total Reviews</div>
                  </div>
                  <div className="bg-orange-50 dark:bg-orange-900/30 rounded-lg p-4">
                    <div className="text-2xl text-orange-600 dark:text-orange-400 mb-1">92%</div>
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
