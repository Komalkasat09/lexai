'use client';

import { useState } from 'react';
import TopBar from '@/components/TopBar';

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    fullName: 'Advocate Sharma',
    email: 'advocate@example.com',
    barCouncilId: '',
    defaultCourt: 'all',
    emailNotifications: true,
    betaFeatures: false,
  });

  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // Here you would normally save to backend
    console.log('Saving settings:', settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <>
      <TopBar title="Settings" />

      <div className="h-[calc(100vh-4rem-3rem)] overflow-y-auto bg-[#F8F9FA]">
        <div className="max-w-4xl mx-auto p-6">
          {/* Profile Settings */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile Information</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={settings.fullName}
                  onChange={(e) => setSettings({ ...settings, fullName: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={settings.email}
                  onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Bar Council ID (Optional)
                </label>
                <input
                  type="text"
                  value={settings.barCouncilId}
                  onChange={(e) => setSettings({ ...settings, barCouncilId: e.target.value })}
                  placeholder="e.g., D/1234/2020"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>
            </div>
          </div>

          {/* Default Preferences */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Default Preferences</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Default Court Filter
                </label>
                <select
                  value={settings.defaultCourt}
                  onChange={(e) => setSettings({ ...settings, defaultCourt: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                >
                  <option value="all">All Courts</option>
                  <option value="sc">Supreme Court of India</option>
                  <option value="delhi-hc">Delhi High Court</option>
                  <option value="bombay-hc">Bombay High Court</option>
                  <option value="madras-hc">Madras High Court</option>
                </select>
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Notifications</h2>
            
            <div className="space-y-4">
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="font-medium text-gray-900">Email Notifications</p>
                  <p className="text-sm text-gray-500">Receive updates about new features and legal updates</p>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.emailNotifications}
                    onChange={(e) => setSettings({ ...settings, emailNotifications: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-[#2E5499] rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-[#2E5499] after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                </div>
              </label>
            </div>
          </div>

          {/* Advanced */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Advanced</h2>
            
            <div className="space-y-4">
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="font-medium text-gray-900">Beta Features</p>
                  <p className="text-sm text-gray-500">Get early access to experimental features</p>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.betaFeatures}
                    onChange={(e) => setSettings({ ...settings, betaFeatures: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-[#2E5499] rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-[#2E5499] after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                </div>
              </label>

              <div className="pt-4 border-t border-gray-200">
                <button className="text-sm text-red-600 hover:text-red-800 font-medium">
                  Clear Search History
                </button>
              </div>
            </div>
          </div>

          {/* About */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">About LexAI</h2>
            
            <div className="space-y-3 text-sm text-gray-600">
              <p>
                <span className="font-semibold">Version:</span> 1.0.0 (Beta)
              </p>
              <p>
                <span className="font-semibold">Last Updated:</span> December 2024
              </p>
              <p className="pt-3 border-t border-gray-200">
                LexAI is an AI-powered legal research assistant designed for Indian lawyers. 
                It provides intelligent search across statutes, case law, and contract analysis 
                with awareness of recent legal reforms including BNS, BNSS, and BSA.
              </p>
              <div className="pt-3 flex gap-4">
                <a href="#" className="text-[#2E5499] hover:text-[#1F3864] font-medium">
                  Privacy Policy
                </a>
                <a href="#" className="text-[#2E5499] hover:text-[#1F3864] font-medium">
                  Terms of Service
                </a>
                <a href="#" className="text-[#2E5499] hover:text-[#1F3864] font-medium">
                  Documentation
                </a>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              className="px-6 py-3 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] transition-colors font-medium"
            >
              Save Changes
            </button>
            {saved && (
              <span className="text-sm text-green-600 flex items-center gap-1">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Settings saved
              </span>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
