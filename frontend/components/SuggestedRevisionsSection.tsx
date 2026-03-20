"use client";

import { useState } from "react";
import { SuggestedRevision } from "@/lib/types";

interface SuggestedRevisionsSectionProps {
  suggestedRevisions: SuggestedRevision[];
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="px-3 py-1.5 text-sm font-medium text-accent border border-accent rounded-md hover:bg-accent hover:text-white transition-colors no-print"
      title="Copy to clipboard"
    >
      {copied ? (
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
          Copied!
        </span>
      ) : (
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          Copy
        </span>
      )}
    </button>
  );
}

export default function SuggestedRevisionsSection({
  suggestedRevisions,
}: SuggestedRevisionsSectionProps) {
  if (!suggestedRevisions || suggestedRevisions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p className="text-lg">✓ No revisions suggested</p>
        <p className="text-sm mt-2">All clauses are acceptable as written.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {suggestedRevisions.map((revision, index) => (
        <div key={index} className="print-break-inside-avoid">
          <h3 className="text-base font-semibold text-navy mb-4">
            {revision?.clause_heading || "Untitled Revision"}
          </h3>

          <div className="space-y-4">
            {/* Original Issue */}
            <div>
              <div className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                Issue Identified
              </div>
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-900">
                  {revision?.original_issue || "No issue description available"}
                </p>
              </div>
            </div>

            {/* Revised Text */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-semibold text-accent uppercase tracking-wide">
                  Suggested Revision
                </div>
                <CopyButton text={revision?.revised_clause || ""} />
              </div>
              <div className="bg-blue-50 border-2 border-accent rounded-lg p-4">
                <p className="text-sm text-navy leading-relaxed whitespace-pre-wrap">
                  {revision?.revised_clause || "No suggested revision available"}
                </p>
              </div>
            </div>

            {/* Key Changes */}
            {revision?.key_changes && (
              <div>
                <div className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">
                  Key Changes
                </div>
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm text-green-900">
                    {revision.key_changes}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
