'use client';

import { useState } from 'react';
import TopBar from '@/components/TopBar';
import SectionCard from '@/components/SectionCard';
import SidePanel from '@/components/SidePanel';

interface Section {
  section_number: string;
  title: string;
  act: string;
  full_text: string;
  simple_explanation: string;
  punishment?: string;
  bns_equivalent?: string;
  amendment_history?: Array<{
    year: number;
    description: string;
  }>;
  related_cases?: Array<{
    name: string;
    citation: string;
  }>;
}

export default function SectionsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAct, setSelectedAct] = useState('all');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<Section[]>([]);
  const [selectedSection, setSelectedSection] = useState<Section | null>(null);

  const acts = [
    { id: 'all', label: 'All Acts' },
    { id: 'ipc', label: 'IPC (Indian Penal Code, 1860)' },
    { id: 'bns', label: 'BNS (Bharatiya Nyaya Sanhita, 2023)' },
    { id: 'crpc', label: 'CrPC (Code of Criminal Procedure, 1973)' },
    { id: 'bnss', label: 'BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)' },
    { id: 'contract', label: 'Indian Contract Act, 1872' },
    { id: 'companies', label: 'Companies Act, 2013' },
    { id: 'evidence', label: 'Indian Evidence Act, 1872' },
  ];

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;

    setSearching(true);

    try {
      const params = new URLSearchParams({
        query: searchTerm,
        ...(selectedAct !== 'all' && { act: selectedAct }),
      });

      const response = await fetch(
        `http://localhost:8000/api/search/sections?${params.toString()}`
      );

      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      setResults(data.sections || []);
    } catch (error) {
      console.error('Error searching sections:', error);
      alert('Failed to search sections. Please ensure the backend is running.');
    } finally {
      setSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <>
      <TopBar title="Section Search" />

      <div className="h-[calc(100vh-4rem-3rem)] overflow-y-auto bg-[#F8F9FA]">
        <div className="max-w-5xl mx-auto p-6">
          {/* Search Bar */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6 shadow-sm">
            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Select Act</label>
              <select
                value={selectedAct}
                onChange={(e) => setSelectedAct(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
              >
                {acts.map((act) => (
                  <option key={act.id} value={act.id}>
                    {act.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Search Sections
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter section number, keyword, or description..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
                <button
                  onClick={handleSearch}
                  disabled={searching || !searchTerm.trim()}
                  className="px-6 py-3 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Examples: "Section 302", "theft", "punishment for murder"
              </p>
            </div>
          </div>

          {/* Results */}
          {results.length > 0 ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Found <span className="font-semibold">{results.length}</span> section
                {results.length > 1 ? 's' : ''}
              </p>
              {results.map((section, idx) => (
                <SectionCard
                  key={idx}
                  section={section}
                  onClick={() => setSelectedSection(section)}
                />
              ))}
            </div>
          ) : searchTerm && !searching ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No sections found for "{searchTerm}"</p>
              <p className="text-sm text-gray-400 mt-2">Try different keywords or section numbers</p>
            </div>
          ) : !searchTerm ? (
            <div className="text-center py-12 text-gray-400">
              <svg
                className="mx-auto h-16 w-16 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <p>Search for sections by number, keyword, or topic</p>
            </div>
          ) : null}
        </div>
      </div>

      {/* Side Panel for Full Section Details */}
      <SidePanel
        isOpen={selectedSection !== null}
        title={selectedSection ? `${selectedSection.section_number} - ${selectedSection.title}` : ''}
        onClose={() => setSelectedSection(null)}
      >
          {selectedSection && (
          <div className="space-y-4">
            {/* Act Badge */}
            <div>
              <span className="px-3 py-1.5 bg-blue-100 text-blue-800 text-sm font-semibold rounded">
                {selectedSection.act}
              </span>
            </div>

            {/* Full Text */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">Full Text</h3>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p
                  className="text-sm text-gray-800 leading-relaxed"
                  style={{ fontFamily: 'Georgia, serif' }}
                >
                  {selectedSection.full_text}
                </p>
              </div>
            </div>

            {/* Simple Explanation */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                Simple Explanation
              </h3>
              <p className="text-sm text-gray-700 leading-relaxed">
                {selectedSection.simple_explanation}
              </p>
            </div>

            {/* Punishment */}
            {selectedSection.punishment && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">Punishment</h3>
                <div className="p-3 bg-red-50 rounded border border-red-200">
                  <p className="text-sm text-red-800">{selectedSection.punishment}</p>
                </div>
              </div>
            )}

            {/* BNS Equivalent */}
            {selectedSection.bns_equivalent && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                  BNS Transition
                </h3>
                <div className="p-3 bg-amber-50 rounded border border-amber-300">
                  <div className="flex items-start gap-2">
                    <span className="text-lg">⚠️</span>
                    <div>
                      <p className="text-sm text-amber-800">
                        Now codified as{' '}
                        <span className="font-semibold">{selectedSection.bns_equivalent}</span>{' '}
                        under Bharatiya Nyaya Sanhita, 2023
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Amendment History */}
            {selectedSection.amendment_history && selectedSection.amendment_history.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-3">
                  Amendment History
                </h3>
                <div className="space-y-3">
                  {selectedSection.amendment_history.map((amendment, idx) => (
                    <div key={idx} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-3 h-3 bg-[#2E5499] rounded-full"></div>
                        {idx < selectedSection.amendment_history!.length - 1 && (
                          <div className="w-0.5 h-full bg-gray-300 mt-1"></div>
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className="text-xs font-semibold text-gray-500 mb-1">
                          {amendment.year}
                        </p>
                        <p className="text-sm text-gray-700">{amendment.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Related Cases */}
            {selectedSection.related_cases && selectedSection.related_cases.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                  Related Case Law
                </h3>
                <div className="space-y-2">
                  {selectedSection.related_cases.map((caseData, idx) => (
                    <button
                      key={idx}
                      className="w-full text-left p-3 bg-purple-50 rounded border border-purple-200 hover:bg-purple-100 transition-colors"
                    >
                      <p className="text-sm font-medium text-gray-900">{caseData.name}</p>
                      <p className="text-xs text-purple-700 mt-1">{caseData.citation}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Copy Button */}
            <button className="w-full px-4 py-2.5 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] transition-colors font-medium">
              Copy Section Text
            </button>
          </div>
          )}
      </SidePanel>
    </>
  );
}
