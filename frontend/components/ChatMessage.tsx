'use client';

import { useState } from 'react';
import CitationChip from './CitationChip';

interface Source {
  type: string;
  text: string;
  metadata: Record<string, any>;
}

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  sources?: {
    bare_acts?: Source[];
    case_law?: Source[];
    amendments?: Source[];
  };
  warnings?: string[];
  trigger_uncertainty?: boolean;
  onSectionClick?: (section: string) => void;
  onCaseClick?: (citation: string) => void;
  onFeedback?: (helpful: boolean) => void;
}

export default function ChatMessage({
  role,
  content,
  timestamp,
  confidence,
  sources,
  warnings,
  trigger_uncertainty,
  onSectionClick,
  onCaseClick,
  onFeedback,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-3xl">
          <div className="bg-[#1F3864] text-white rounded-lg px-4 py-3 shadow-sm">
            <p className="text-sm leading-relaxed">{content}</p>
          </div>
          {timestamp && (
            <p className="text-xs text-gray-400 mt-1 text-right">{timestamp}</p>
          )}
        </div>
      </div>
    );
  }

  const isUncertain = trigger_uncertainty || confidence === 'LOW';
  const borderColor = isUncertain
    ? 'border-[#E67E22]'
    : confidence === 'MEDIUM'
    ? 'border-[#2E5499]'
    : 'border-gray-200';

  return (
    <div className="flex justify-start mb-6">
      <div className={`max-w-4xl w-full bg-white rounded-lg border-2 ${borderColor} shadow-sm overflow-hidden`}>
        {/* Answer Section */}
        <div className="p-6">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Answer
          </h3>
          <div
            className="prose prose-sm max-w-none"
            style={{ fontFamily: 'Georgia, serif' }}
          >
            <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
              {content}
            </p>
          </div>
        </div>

        {/* Legal Basis - Sections */}
        {sources?.bare_acts && sources.bare_acts.length > 0 && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Legal Basis
            </h3>
            <div className="flex flex-wrap gap-2">
              {sources.bare_acts.map((source, idx) => (
                <CitationChip
                  key={idx}
                  type="section"
                  text={source.metadata?.section || source.text?.substring(0, 30) || 'Unknown Section'}
                  onClick={() => onSectionClick?.(source.text)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Case Law References */}
        {sources?.case_law && sources.case_law.length > 0 && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Case Law References
            </h3>
            <div className="flex flex-wrap gap-2">
              {sources.case_law.map((source, idx) => (
                <CitationChip
                  key={idx}
                  type="case"
                  text={source.metadata?.citation || source.text?.substring(0, 40) || 'Unknown Citation'}
                  onClick={() => onCaseClick?.(source.text)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Amendment Notes */}
        {sources?.amendments && sources.amendments.length > 0 && (
          <div className="px-6 py-4 bg-amber-50 border-t border-amber-100">
            <h3 className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-2 flex items-center gap-2">
              <span>⚠️</span> Amendment Notes
            </h3>
            <div className="space-y-2">
              {sources.amendments.map((amendment, idx) => (
                <div key={idx} className="text-sm text-amber-900">
                  {amendment.text}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* BNS/BNSS Transition Note */}
        {warnings && warnings.some((w) => w.includes('BNS') || w.includes('BNSS')) && (
          <div className="px-6 py-4 bg-blue-50 border-t border-blue-100">
            <h3 className="text-xs font-semibold text-blue-800 uppercase tracking-wide mb-2 flex items-center gap-2">
              <span>🔄</span> BNS/BNSS Transition Note
            </h3>
            <div className="space-y-1">
              {warnings
                .filter((w) => w.includes('BNS') || w.includes('BNSS'))
                .map((warning, idx) => (
                  <p key={idx} className="text-sm text-blue-900">
                    {warning}
                  </p>
                ))}
            </div>
          </div>
        )}

        {/* Other Warnings */}
        {warnings && warnings.some((w) => !w.includes('BNS') && !w.includes('BNSS')) && (
          <div className="px-6 py-4 bg-amber-50 border-t border-amber-100">
            <h3 className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-2">
              ⚠️ Warnings
            </h3>
            <div className="space-y-1">
              {warnings
                .filter((w) => !w.includes('BNS') && !w.includes('BNSS'))
                .map((warning, idx) => (
                  <p key={idx} className="text-sm text-amber-900">
                    {warning}
                  </p>
                ))}
            </div>
          </div>
        )}

        {/* Footer - Confidence & Actions */}
        <div className="px-6 py-4 bg-white border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {confidence && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Confidence:</span>
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className={`w-2 h-2 rounded-full ${
                          confidence === 'HIGH'
                            ? i <= 4
                              ? 'bg-green-500'
                              : 'bg-gray-200'
                            : confidence === 'MEDIUM'
                            ? i <= 3
                              ? 'bg-yellow-500'
                              : 'bg-gray-200'
                            : i <= 2
                            ? 'bg-red-500'
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  <span className={`text-xs font-medium ${
                    confidence === 'HIGH'
                      ? 'text-green-700'
                      : confidence === 'MEDIUM'
                      ? 'text-yellow-700'
                      : 'text-red-700'
                  }`}>
                    {confidence}
                  </span>
                </div>
              )}

              {onFeedback && (
                <div className="flex items-center gap-2 pl-4 border-l border-gray-200">
                  <button
                    onClick={() => onFeedback(true)}
                    className="text-gray-400 hover:text-green-600 transition-colors"
                    title="Helpful"
                  >
                    👍
                  </button>
                  <button
                    onClick={() => onFeedback(false)}
                    className="text-gray-400 hover:text-red-600 transition-colors"
                    title="Not accurate"
                  >
                    👎
                  </button>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
              >
                {copied ? '✓ Copied' : 'Copy answer'}
              </button>
              <button className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors">
                Download PDF
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
