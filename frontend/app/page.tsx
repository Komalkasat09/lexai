'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const [showSignIn, setShowSignIn] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    // Simple mock authentication - redirect to dashboard
    router.push('/dashboard/research');
  };

  if (showSignIn) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-lg shadow-lg p-8">
            {/* Logo */}
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold text-[#1F3864]">
                LexAI<span className="text-[#C8A951]">.</span>
              </h1>
              <p className="text-sm text-gray-600 mt-2">Sign in to continue</p>
            </div>

            {/* Sign In Form */}
            <form onSubmit={handleSignIn} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2E5499] focus:border-transparent"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2E5499] focus:border-transparent"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-[#2E5499] text-white py-2.5 rounded-lg hover:bg-[#1F3864] transition-colors font-medium"
              >
                Sign In
              </button>
            </form>

            {/* Back to landing */}
            <button
              onClick={() => setShowSignIn(false)}
              className="w-full mt-4 text-sm text-gray-600 hover:text-gray-900"
            >
              ← Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F8F9FA] to-white flex flex-col">
      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-3xl mx-auto text-center">
          {/* Logo */}
          <h1 className="text-6xl font-bold text-[#1F3864] mb-4">
            LexAI<span className="text-[#C8A951]">.</span>
          </h1>

          {/* Tagline */}
          <h2 className="text-2xl font-semibold text-gray-700 mb-3">
            Legal Research Assistant for Indian Lawyers
          </h2>

          {/* Sub-tagline */}
          <p className="text-lg text-gray-600 mb-12 max-w-2xl mx-auto">
            Powered by Supreme Court judgments, High Court decisions, and updated Bare Acts
          </p>

          {/* Action Buttons */}
          <div className="flex gap-4 justify-center mb-16">
            <button
              onClick={() => setShowSignIn(true)}
              className="px-8 py-3 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] transition-colors font-medium text-lg shadow-sm"
            >
              Sign In
            </button>
            <button className="px-8 py-3 bg-white text-[#2E5499] border-2 border-[#2E5499] rounded-lg hover:bg-[#2E5499] hover:text-white transition-colors font-medium text-lg shadow-sm">
              Request Access
            </button>
          </div>

          {/* Disclaimer */}
          <div className="max-w-2xl mx-auto p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <p className="text-sm text-gray-600 leading-relaxed">
              LexAI is a research tool. All outputs should be verified by a qualified lawyer before
              use.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="p-6 text-center text-sm text-gray-500">
        <p>© 2026 LexAI. All rights reserved.</p>
      </footer>
    </div>
  );
}
