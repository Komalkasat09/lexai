'use client';

import { useState, useRef } from 'react';
import TopBar from '@/components/TopBar';
import RiskBadge from '@/components/RiskBadge';

interface Clause {
  name: string;
  type: string;
  risk_level: 'high' | 'moderate' | 'standard' | 'low';
  text: string;
  suggested_revision?: string;
  explanation?: string;
}

interface ContractAnalysis {
  overview: {
    parties: string[];
    effective_date: string;
    termination_date?: string;
    governing_law: string;
    type: string;
  };
  clauses: Clause[];
  missing_clauses: string[];
  risk_summary: {
    high: number;
    moderate: number;
    standard: number;
  };
}

type TabType = 'overview' | 'clauses' | 'risks' | 'missing' | 'revisions';

export default function ContractsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<ContractAnalysis | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [expandedClause, setExpandedClause] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;

    setAnalyzing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Analysis failed');

      const data = await response.json();
      setAnalysis(data);
      setActiveTab('overview');
    } catch (error) {
      console.error('Error analyzing contract:', error);
      alert('Failed to analyze contract. Please ensure the backend is running.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleNewAnalysis = () => {
    setFile(null);
    setAnalysis(null);
    setActiveTab('overview');
    setExpandedClause(null);
  };

  const scrollToClause = (index: number) => {
    setActiveTab('clauses');
    setExpandedClause(index);
  };

  return (
    <>
      <TopBar title="Contract Review" />

      <div className="flex h-[calc(100vh-4rem-3rem)]">
        {/* LEFT PANEL - Upload / Navigation */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          {!analysis ? (
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Upload Contract</h3>
              
              {/* Drag & Drop Area */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-[#2E5499] transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="mb-4">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-400"
                    stroke="currentColor"
                    fill="none"
                    viewBox="0 0 48 48"
                  >
                    <path
                      d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <p className="text-sm text-gray-600 mb-1">
                  {file ? file.name : 'Drop contract here or click to browse'}
                </p>
                <p className="text-xs text-gray-400">PDF, DOCX up to 10MB</p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc"
                onChange={handleFileSelect}
                className="hidden"
              />

              {file && (
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="w-full mt-4 px-4 py-3 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {analyzing ? 'Analyzing...' : 'Analyze Contract'}
                </button>
              )}
            </div>
          ) : (
            <>
              {/* File Info */}
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{file?.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {(file?.size || 0 / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    onClick={handleNewAnalysis}
                    className="ml-2 px-3 py-1 text-xs text-[#2E5499] hover:bg-gray-50 rounded transition-colors"
                  >
                    New
                  </button>
                </div>

                {/* Risk Summary */}
                <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                  <p className="text-xs font-semibold text-gray-600 uppercase">Risk Summary</p>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-red-700">🔴 High Risk</span>
                      <span className="font-semibold">{analysis.risk_summary.high}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-yellow-700">🟡 Moderate</span>
                      <span className="font-semibold">{analysis.risk_summary.moderate}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-green-700">🟢 Standard</span>
                      <span className="font-semibold">{analysis.risk_summary.standard}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Clause Navigation */}
              <div className="flex-1 overflow-y-auto p-4">
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3">Clauses</h4>
                <div className="space-y-2">
                  {analysis.clauses.map((clause, idx) => (
                    <button
                      key={idx}
                      onClick={() => scrollToClause(idx)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                        expandedClause === idx
                          ? 'bg-[#2E5499] text-white'
                          : 'hover:bg-gray-100 text-gray-700'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className="text-lg flex-shrink-0">
                          {clause.risk_level === 'high'
                            ? '🔴'
                            : clause.risk_level === 'moderate'
                            ? '🟡'
                            : '🟢'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{clause.name}</p>
                          <p className="text-xs opacity-75 mt-0.5">{clause.type}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* RIGHT PANEL - Analysis Results */}
        <div className="flex-1 flex flex-col bg-[#F8F9FA]">
          {analysis ? (
            <>
              {/* Tabs */}
              <div className="bg-white border-b border-gray-200 px-6">
                <div className="flex gap-1">
                  {[
                    { id: 'overview', label: 'Overview' },
                    { id: 'clauses', label: 'Clauses' },
                    { id: 'risks', label: 'Risks' },
                    { id: 'missing', label: 'Missing' },
                    { id: 'revisions', label: 'Revisions' },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as TabType)}
                      className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                        activeTab === tab.id
                          ? 'border-[#2E5499] text-[#2E5499]'
                          : 'border-transparent text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {activeTab === 'overview' && (
                  <div className="max-w-4xl mx-auto space-y-4">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">Contract Overview</h2>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white p-4 rounded-lg border border-gray-200">
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                          Contract Type
                        </p>
                        <p className="text-lg font-medium text-gray-900">
                          {analysis.overview.type}
                        </p>
                      </div>
                      <div className="bg-white p-4 rounded-lg border border-gray-200">
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                          Governing Law
                        </p>
                        <p className="text-lg font-medium text-gray-900">
                          {analysis.overview.governing_law}
                        </p>
                      </div>
                      <div className="bg-white p-4 rounded-lg border border-gray-200">
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                          Effective Date
                        </p>
                        <p className="text-lg font-medium text-gray-900">
                          {analysis.overview.effective_date}
                        </p>
                      </div>
                      {analysis.overview.termination_date && (
                        <div className="bg-white p-4 rounded-lg border border-gray-200">
                          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                            Termination Date
                          </p>
                          <p className="text-lg font-medium text-gray-900">
                            {analysis.overview.termination_date}
                          </p>
                        </div>
                      )}
                      <div className="bg-white p-4 rounded-lg border border-gray-200 col-span-2">
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                          Parties Involved
                        </p>
                        <ul className="list-disc list-inside space-y-1">
                          {analysis.overview.parties.map((party, idx) => (
                            <li key={idx} className="text-sm text-gray-900">
                              {party}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'clauses' && (
                  <div className="max-w-4xl mx-auto">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">All Clauses</h2>
                    <div className="space-y-4">
                      {analysis.clauses.map((clause, idx) => (
                        <div
                          key={idx}
                          className={`bg-white rounded-lg border-2 overflow-hidden transition-all ${
                            expandedClause === idx ? 'border-[#2E5499]' : 'border-gray-200'
                          }`}
                        >
                          <button
                            onClick={() => setExpandedClause(expandedClause === idx ? null : idx)}
                            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <RiskBadge level={clause.risk_level} size="sm" />
                              <div className="text-left">
                                <p className="font-semibold text-gray-900">{clause.name}</p>
                                <p className="text-sm text-gray-500">{clause.type}</p>
                              </div>
                            </div>
                            <svg
                              className={`w-5 h-5 text-gray-400 transition-transform ${
                                expandedClause === idx ? 'rotate-180' : ''
                              }`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 9l-7 7-7-7"
                              />
                            </svg>
                          </button>

                          {expandedClause === idx && (
                            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                              <p
                                className="text-sm text-gray-800 leading-relaxed"
                                style={{ fontFamily: 'Georgia, serif' }}
                              >
                                {clause.text}
                              </p>
                              {clause.explanation && (
                                <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
                                  <p className="text-xs font-semibold text-blue-900 mb-1">
                                    Explanation
                                  </p>
                                  <p className="text-sm text-blue-800">{clause.explanation}</p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'risks' && (
                  <div className="max-w-4xl mx-auto">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">Risk Analysis</h2>
                    <div className="space-y-6">
                      {analysis.clauses
                        .filter((c) => c.risk_level === 'high' || c.risk_level === 'moderate')
                        .map((clause, idx) => (
                          <div
                            key={idx}
                            className={`bg-white rounded-lg border-2 p-6 ${
                              clause.risk_level === 'high'
                                ? 'border-red-300'
                                : 'border-yellow-300'
                            }`}
                          >
                            <div className="flex items-start gap-3 mb-4">
                              <RiskBadge level={clause.risk_level} />
                              <div className="flex-1">
                                <h3 className="text-lg font-semibold text-gray-900">
                                  {clause.name}
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">{clause.type}</p>
                              </div>
                            </div>
                            <div className="mb-4">
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                                Current Text
                              </p>
                              <p
                                className="text-sm text-gray-700 bg-gray-50 p-3 rounded"
                                style={{ fontFamily: 'Georgia, serif' }}
                              >
                                {clause.text}
                              </p>
                            </div>
                            {clause.suggested_revision && (
                              <div>
                                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                                  Suggested Revision
                                </p>
                                <div className="bg-blue-50 p-3 rounded border border-blue-200">
                                  <p
                                    className="text-sm text-gray-900"
                                    style={{ fontFamily: 'Georgia, serif' }}
                                  >
                                    {clause.suggested_revision}
                                  </p>
                                  <button className="mt-3 px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors">
                                    Copy Revision
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {activeTab === 'missing' && (
                  <div className="max-w-4xl mx-auto">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">Missing Clauses</h2>
                    <div className="space-y-3">
                      {analysis.missing_clauses.map((clause, idx) => (
                        <div key={idx} className="bg-white rounded-lg border border-amber-300 p-4">
                          <div className="flex items-start gap-3">
                            <span className="text-xl">⚠️</span>
                            <div className="flex-1">
                              <p className="font-medium text-gray-900">{clause}</p>
                              <p className="text-sm text-gray-600 mt-1">
                                Consider adding this clause for better protection
                              </p>
                            </div>
                            <button className="px-3 py-1 text-xs text-amber-700 hover:bg-amber-50 rounded transition-colors">
                              Add to checklist
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'revisions' && (
                  <div className="max-w-6xl mx-auto">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">
                      Suggested Revisions
                    </h2>
                    <div className="space-y-6">
                      {analysis.clauses
                        .filter((c) => c.suggested_revision)
                        .map((clause, idx) => (
                          <div key={idx} className="bg-white rounded-lg border border-gray-200 p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">
                              {clause.name}
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                                  Current
                                </p>
                                <div className="bg-gray-100 p-4 rounded h-full">
                                  <p
                                    className="text-sm text-gray-700"
                                    style={{ fontFamily: 'Georgia, serif' }}
                                  >
                                    {clause.text}
                                  </p>
                                </div>
                              </div>
                              <div>
                                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                                  Suggested
                                </p>
                                <div className="bg-blue-50 border border-blue-200 p-4 rounded h-full">
                                  <p
                                    className="text-sm text-gray-900"
                                    style={{ fontFamily: 'Georgia, serif' }}
                                  >
                                    {clause.suggested_revision}
                                  </p>
                                </div>
                              </div>
                            </div>
                            <button className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors">
                              Copy Suggested Text
                            </button>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Export Button */}
              <div className="bg-white border-t border-gray-200 px-6 py-4">
                <button
                  onClick={() => window.print()}
                  className="px-6 py-2.5 bg-[#2E5499] text-white rounded-lg hover:bg-[#1F3864] transition-colors font-medium"
                >
                  Download Full Report
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-400">
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
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="text-lg">Upload a contract to begin analysis</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
