'use client';

import { useState } from 'react';
import TopBar from '@/components/TopBar';
import CaseCard from '@/components/CaseCard';
import SidePanel from '@/components/SidePanel';
import CitationChip from '@/components/CitationChip';

interface CaseData {
  name: string;
  citation: string;
  court: string;
  date: string;
  judges?: string[];
  summary: string;
  principle?: string;
  overruled?: boolean;
  overruled_by?: string;
  facts?: string;
  issues?: string[];
  arguments?: {
    petitioner: string;
    respondent: string;
  };
  held?: string;
  sections_cited?: string[];
}

export default function CasesPage() {
  const [searchParams, setSearchParams] = useState({
    keywords: '',
    citation: '',
    judge: '',
    year: '',
    court: 'all',
    acts: [] as string[],
  });
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<CaseData[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseData | null>(null);

  const courts = [
    { id: 'all', label: 'All Courts' },
    { id: 'sc', label: 'Supreme Court of India' },
    { id: 'delhi-hc', label: 'Delhi High Court' },
    { id: 'bombay-hc', label: 'Bombay High Court' },
    { id: 'madras-hc', label: 'Madras High Court' },
    { id: 'calcutta-hc', label: 'Calcutta High Court' },
    { id: 'karnataka-hc', label: 'Karnataka High Court' },
  ];

  const acts = [
    { id: 'ipc', label: 'IPC' },
    { id: 'crpc', label: 'CrPC' },
    { id: 'contract', label: 'Contract Act' },
    { id: 'companies', label: 'Companies Act' },
    { id: 'evidence', label: 'Evidence Act' },
  ];

  const handleSearch = async () => {
    if (!searchParams.keywords.trim() && !searchParams.citation.trim()) return;

    setSearching(true);

    try {
      const params = new URLSearchParams();
      if (searchParams.keywords) params.append('keywords', searchParams.keywords);
      if (searchParams.citation) params.append('citation', searchParams.citation);
      if (searchParams.judge) params.append('judge', searchParams.judge);
      if (searchParams.year) params.append('year', searchParams.year);
      if (searchParams.court !== 'all') params.append('court', searchParams.court);
      if (searchParams.acts.length > 0) params.append('acts', searchParams.acts.join(','));

      const response = await fetch(
        `http://localhost:8000/api/search/cases?${params.toString()}`
      );

      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      setResults(data.cases || []);
    } catch (error) {
      console.error('Error searching cases:', error);
      alert('Failed to search cases. Please ensure the backend is running.');
    } finally {
      setSearching(false);
    }
  };

  const toggleAct = (actId: string) => {
    setSearchParams((prev) => ({
      ...prev,
      acts: prev.acts.includes(actId)
        ? prev.acts.filter((id) => id !== actId)
        : [...prev.acts, actId],
    }));
  };

  return (
    <>
      <TopBar title="Case Law Search" />

      <div className="h-[calc(100vh-4rem-3rem)] overflow-y-auto bg-[#F8F9FA]">
        <div className="max-w-6xl mx-auto p-6">
          {/* Advanced Search Form */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Advanced Search</h2>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Keywords */}
              <div className="col-span-2">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Keywords
                </label>
                <input
                  type="text"
                  value={searchParams.keywords}
                  onChange={(e) =>
                    setSearchParams((prev) => ({ ...prev, keywords: e.target.value }))
                  }
                  placeholder="e.g., breach of contract, negligence, constitutional validity"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>

              {/* Citation */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Citation
                </label>
                <input
                  type="text"
                  value={searchParams.citation}
                  onChange={(e) =>
                    setSearchParams((prev) => ({ ...prev, citation: e.target.value }))
                  }
                  placeholder="e.g., AIR 1978 SC 597"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>

              {/* Judge */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Judge</label>
                <input
                  type="text"
                  value={searchParams.judge}
                  onChange={(e) =>
                    setSearchParams((prev) => ({ ...prev, judge: e.target.value }))
                  }
                  placeholder="e.g., Justice Bhagwati"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>

              {/* Year */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Year</label>
                <input
                  type="text"
                  value={searchParams.year}
                  onChange={(e) =>
                    setSearchParams((prev) => ({ ...prev, year: e.target.value }))
                  }
                  placeholder="e.g., 2023"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                />
              </div>

              {/* Court */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Court</label>
                <select
                  value={searchParams.court}
                  onChange={(e) =>
                    setSearchParams((prev) => ({ ...prev, court: e.target.value }))
                  }
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#2E5499] focus:border-transparent outline-none"
                >
                  {courts.map((court) => (
                    <option key={court.id} value={court.id}>
                      {court.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Acts Filter */}
            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Filter by Acts
              </label>
              <div className="flex flex-wrap gap-2">
                {acts.map((act) => (
                  <button
                    key={act.id}
                    onClick={() => toggleAct(act.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      searchParams.acts.includes(act.id)
                        ? 'bg-[#2E5499] text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {act.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Search Button */}
            <button
              onClick={handleSearch}
              disabled={
                searching ||
                (!searchParams.keywords.trim() && !searchParams.citation.trim())
              }
              className="w-full px-6 py-3 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {searching ? 'Searching...' : 'Search Cases'}
            </button>
          </div>

          {/* Results */}
          {results.length > 0 ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Found <span className="font-semibold">{results.length}</span> case
                {results.length > 1 ? 's' : ''}
              </p>
              {results.map((caseData, idx) => (
                <CaseCard
                  key={idx}
                  caseData={caseData}
                  onClick={() => setSelectedCase(caseData)}
                />
              ))}
            </div>
          ) : searchParams.keywords && !searching ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No cases found matching your criteria</p>
              <p className="text-sm text-gray-400 mt-2">Try adjusting your search parameters</p>
            </div>
          ) : (
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
                  d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
                />
              </svg>
              <p>Use the advanced search to find relevant case law</p>
            </div>
          )}
        </div>
      </div>

      {/* Side Panel for Full Case Details */}
      <SidePanel 
        isOpen={selectedCase !== null}
        title={selectedCase?.name || ''} 
        onClose={() => setSelectedCase(null)}
      >
          {selectedCase && (
          <div className="space-y-4">
            {/* Overruled Warning */}
            {selectedCase.overruled && (
              <div className="p-4 bg-red-50 rounded border-2 border-red-500">
                <div className="flex items-start gap-2">
                  <span className="text-2xl">⛔</span>
                  <div>
                    <p className="text-sm font-bold text-red-900 uppercase mb-1">Overruled</p>
                    <p className="text-sm text-red-800">
                      This judgment has been overruled
                      {selectedCase.overruled_by && ` by ${selectedCase.overruled_by}`}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Citation & Court Info */}
            <div>
              <div className="flex flex-wrap gap-2 mb-2">
                <span className="px-3 py-1.5 bg-purple-100 text-purple-800 text-sm font-semibold rounded">
                  {selectedCase.citation}
                </span>
              </div>
              <p className="text-sm text-gray-600">{selectedCase.court}</p>
              <p className="text-sm text-gray-600">{selectedCase.date}</p>
            </div>

            {/* Judges */}
            {selectedCase.judges && selectedCase.judges.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">Bench</h3>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {selectedCase.judges.map((judge, idx) => (
                    <li key={idx}>{judge}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Facts */}
            {selectedCase.facts && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">Facts</h3>
                <p
                  className="text-sm text-gray-800 leading-relaxed"
                  style={{ fontFamily: 'Georgia, serif' }}
                >
                  {selectedCase.facts}
                </p>
              </div>
            )}

            {/* Issues */}
            {selectedCase.issues && selectedCase.issues.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                  Issues Raised
                </h3>
                <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
                  {selectedCase.issues.map((issue, idx) => (
                    <li key={idx} style={{ fontFamily: 'Georgia, serif' }}>
                      {issue}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Arguments */}
            {selectedCase.arguments && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">Arguments</h3>
                <div className="space-y-3">
                  <div className="p-3 bg-blue-50 rounded">
                    <p className="text-xs font-semibold text-blue-900 mb-1">Petitioner</p>
                    <p className="text-sm text-gray-800">{selectedCase.arguments.petitioner}</p>
                  </div>
                  <div className="p-3 bg-amber-50 rounded">
                    <p className="text-xs font-semibold text-amber-900 mb-1">Respondent</p>
                    <p className="text-sm text-gray-800">{selectedCase.arguments.respondent}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Held */}
            {selectedCase.held && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">Held</h3>
                <div className="p-4 bg-green-50 rounded border border-green-200">
                  <p
                    className="text-sm text-gray-900 leading-relaxed"
                    style={{ fontFamily: 'Georgia, serif' }}
                  >
                    {selectedCase.held}
                  </p>
                </div>
              </div>
            )}

            {/* Legal Principle */}
            {selectedCase.principle && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                  Legal Principle
                </h3>
                <div className="p-4 bg-blue-50 rounded border-l-4 border-blue-500">
                  <p
                    className="text-sm text-blue-900 leading-relaxed font-medium"
                    style={{ fontFamily: 'Georgia, serif' }}
                  >
                    {selectedCase.principle}
                  </p>
                </div>
              </div>
            )}

            {/* Sections Cited */}
            {selectedCase.sections_cited && selectedCase.sections_cited.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                  Sections Cited
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedCase.sections_cited.map((section, idx) => (
                    <CitationChip key={idx} text={section} type="section" onClick={() => {}} />
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="pt-4 border-t border-gray-200 space-y-2">
              <button className="w-full px-4 py-2.5 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] transition-colors font-medium">
                Copy Citation
              </button>
              <button className="w-full px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium">
                Download Full Judgment
              </button>
            </div>
          </div>
          )}
      </SidePanel>
    </>
  );
}
