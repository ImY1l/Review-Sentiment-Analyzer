import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { 
  Brain, 
  ShoppingBag,
  UtensilsCrossed, 
  MapPin 
} from 'lucide-react';

const CATEGORIES = [
  { id: 'ecommerce', name: 'E-commerce', icon: ShoppingBag, color: 'from-blue-500 to-indigo-500' },
  { id: 'food', name: 'Food & dining', icon: UtensilsCrossed, color: 'from-orange-500 to-red-500' },
  { id: 'locations', name: 'Locations', icon: MapPin, color: 'from-green-500 to-emerald-500' },
];


export function CategorySelectionPage() {
  const navigate = useNavigate();
  const { user, setCategory } = useApp();
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [error, setError] = useState('');

  const handleCategorySelect = (categoryId: string) => {
    setSelectedCategory(categoryId);
    setError('');
  };

  const handleContinue = () => {
    if (!selectedCategory) {
      setError('Please select a category to continue');
      return;
    }

    setCategory(selectedCategory);
    navigate('/search');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950 p-6 lg:p-12">
      <div className="max-w-7xl mx-auto">
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
            First, select the category that best matches what you want to review
          </p>
        </div>

        {/* Category Grid */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
            Choose a Category
          </h2>
          

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-40 mb-8">

            {CATEGORIES.map((category) => {
              const Icon = category.icon;
              const isSelected = selectedCategory === category.id;
              
              return (
                <button
                  key={category.id}
                  onClick={() => handleCategorySelect(category.id)}
                  className={`
                    relative h-full flex flex-col justify-between p-4 rounded-xl border-2 transition-all duration-200
                    ${isSelected 
                      ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 shadow-lg scale-105' 
                      : 'border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-md'
                    }
                  `}
                >
                  <div className="flex flex-col items-center text-center gap-2 flex-1 justify-center">
                    <div className={`bg-gradient-to-br ${category.color} p-3 rounded-lg shadow-md`}>
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    <span className="font-medium text-gray-900 dark:text-white text-base">
                      {category.name}
                    </span>
                  </div>
                  
                  {isSelected && (
                    <div className="absolute top-2 right-2 w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center shadow-lg">
                      <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              );
            })}
          </div>





          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Continue Button */}
          <button
            onClick={handleContinue}
            disabled={!selectedCategory}
            className={`
              w-full px-6 py-4 rounded-xl shadow-lg font-semibold text-lg transition-all duration-200
              ${selectedCategory
                ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:shadow-xl transform hover:scale-[1.02]'
                : 'bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              }
            `}
          >
            Continue to Product Search
          </button>
        </div>
      </div>
    </div>
  );
}
