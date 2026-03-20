'use client';

import { useState, useEffect } from 'react';
import TopBar from '@/components/TopBar';

interface QueryHistory {
  id: number;
  query_text: string;
  query_type: 'research' | 'contract' | 'section' | 'case';
  timestamp: string;
  was_answered: boolean;
}

export default function HistoryPage() {
  const [queries, setQueries] = useState<QueryHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'research' | 'contract' | 'section' | 'case'>('all');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/history');
      
      if (response.ok) {
        const data = await response.json();
        setQueries(data.queries || []);
      } else {
        // Backend endpoint not implemented yet - show empty state
        setQueries([]);
      }
    } catch (error) {
      console.error('Error fetching history:', error);
      // Network error or backend unavailable - show empty state
      setQueries([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredQueries = filter === 'all' 
    ? queries 
    : queries.filter(q => q.query_type === filter);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'research': return 'bg-blue-100 text-blue-800';
      case 'contract': return 'bg-purple-100 text-purple-800';
      case 'section': return 'bg-green-100 text-green-800';
      case 'case': return 'bg-amber-100 text-amber-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'research': return 'Legal Research';
      case 'contract': return 'Contract Review';
      case 'section': return 'Section Search';
      case 'case': return 'Case Law';
      default: return type;
    }
  };

  const handleQueryClick = (query: QueryHistory) => {
    // Navigate based on query type
    switch (query.query_type) {
      case 'research':
        window.location.href = '/dashboard/research';
        break;
      case 'contract':
        window.location.href = '/dashboard/contracts';
        break;
      case 'section':
        window.location.href = '/dashboard/sections';
        break;
      case 'case':
        window.location.href = '/dashboard/cases';
        break;
    }
  };

  return (
    <>
      <TopBar title="Recent Queries" />

      <div className="h-[calc(100vh-4rem-3rem)] overflow-y-auto bg-[#F8F9FA]">
        <div className="max-w-6xl mx-auto p-6">
          {/* Filters */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-700">Filter by:</span>
              <div className="flex gap-2">
                {[
                  { id: 'all', label: 'All' },
                  { id: 'research', label: 'Legal Research' },
                  { id: 'contract', label: 'Contracts' },
                  { id: 'section', label: 'Sections' },
                  { id: 'case', label: 'Cases' },
                ].map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setFilter(type.id as any)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      filter === type.id
                        ? 'bg-[#2E5499] text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Results Count */}
          {!loading && (
            <p className="text-sm text-gray-600 mb-4">
              {filteredQueries.length} {filter !== 'all' ? getTypeLabel(filter).toLowerCase() : ''}{' '}
              quer{filteredQueries.length === 1 ? 'y' : 'ies'}
            </p>
          )}

          {/* Query List */}
          {loading ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading history...</p>
            </div>
          ) : filteredQueries.length > 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                      Query
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                      Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                      Status
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredQueries.map((query) => (
                    <tr key={query.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <p className="text-sm text-gray-900 line-clamp-2">{query.query_text}</p>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getTypeColor(query.query_type)}`}>
                          {getTypeLabel(query.query_type)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-sm text-gray-600">{formatTimestamp(query.timestamp)}</p>
                      </td>
                      <td className="px-6 py-4">
                        {query.was_answered ? (
                          <span className="inline-flex items-center gap-1 text-sm text-green-700">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Answered
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-sm text-amber-700">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                            No result
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleQueryClick(query)}
                          className="text-sm text-[#2E5499] hover:text-[#1F3864] font-medium"
                        >
                          Rerun →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p>No queries found</p>
              <p className="text-sm mt-2">Your search history will appear here</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
