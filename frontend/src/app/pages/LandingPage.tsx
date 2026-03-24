import React from "react";
import { useNavigate } from "react-router-dom";
import {
  Brain,
  Sparkles,
  TrendingUp,
  Shield,
} from "lucide-react";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-purple-900 dark:to-indigo-950">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16 md:py-24">
        <div className="flex flex-col items-center text-center space-y-8">
          {/* Logo and Title */}
          <div className="space-y-4">
            <div className="flex flex-col items-center justify-center space-x-3">
              <div className="bg-gradient-to-br from-purple-600 to-blue-600 p-4 rounded-2xl shadow-xl">
                <Brain className="w-12 h-12 md:w-16 md:h-16 text-white" />
              </div>
              <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-purple-600 via-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Review Sentiment Analyzer
              </h1>
            </div>

            <p className="text-xl md:text-3xl text-gray-700 dark:text-gray-200 max-w-3xl mx-auto">
              Harness AI to analyze thousands of reviews in
              seconds
            </p>

            <p className="text-base md:text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              Make smarter decisions with comprehensive review
              analysis from across the internet
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 mt-8">
            <button
              onClick={() => navigate("/login")}
              className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 text-lg font-semibold"
            >
              Login
            </button>
            <button
              onClick={() => navigate("/register")}
              className="px-8 py-4 bg-white dark:bg-gray-800 text-purple-600 dark:text-purple-400 rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 text-lg font-semibold border-2 border-purple-200 dark:border-purple-800"
            >
              Get Started
            </button>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 w-full max-w-5xl">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
              <div className="bg-gradient-to-br from-purple-500 to-purple-600 p-3 rounded-lg w-fit mb-4">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                AI-Powered Analysis
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Advanced machine learning algorithms analyze
                sentiment, patterns, and insights from reviews
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
              <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-3 rounded-lg w-fit mb-4">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                Multi-Platform Scraping
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Aggregate reviews from Amazon, Yelp,
                TripAdvisor, and more in one comprehensive view
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
              <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 p-3 rounded-lg w-fit mb-4">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                Visual Insights
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Interactive charts and graphs help you
                understand review trends at a glance
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}