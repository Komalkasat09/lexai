"use client";

import { ContractAnalysis } from "@/lib/types";
import CollapsibleSection from "./CollapsibleSection";
import ContractOverviewSection from "./ContractOverviewSection";
import ClauseSummarySection from "./ClauseSummarySection";
import RiskAnalysisSection from "./RiskAnalysisSection";
import MissingClausesSection from "./MissingClausesSection";
import SuggestedRevisionsSection from "./SuggestedRevisionsSection";

interface ResultsProps {
  analysis: ContractAnalysis;
  filename: string;
  onNewAnalysis: () => void;
}

export default function Results({ analysis, filename, onNewAnalysis }: ResultsProps) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header with Export Button */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6 print-break-inside-avoid">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-2xl font-bold text-navy mb-2">Contract Analysis Report</h1>
              <p className="text-sm text-gray-600">File: {filename}</p>
            </div>
            <div className="flex gap-3 no-print">
              <button
                onClick={handlePrint}
                className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors font-medium text-sm flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Download Report as PDF
              </button>
              <button
                onClick={onNewAnalysis}
                className="px-4 py-2 border border-gray-300 text-navy rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm"
              >
                New Analysis
              </button>
            </div>
          </div>
        </div>

        {/* Analysis Sections */}
        <div className="space-y-4">
          {/* Section 1: Contract Overview */}
          <CollapsibleSection title="Contract Overview" number={1}>
            <ContractOverviewSection overview={analysis.overview} />
          </CollapsibleSection>

          {/* Section 2: Clause Summary */}
          <CollapsibleSection title="Clause Summary" number={2}>
            <ClauseSummarySection clauses={analysis.clauses} risks={analysis.risks} />
          </CollapsibleSection>

          {/* Section 3: Risk Analysis */}
          <CollapsibleSection title="Risk Analysis" number={3}>
            <RiskAnalysisSection
              risks={analysis.risks}
              suggestedRevisions={analysis.suggested_revisions}
            />
          </CollapsibleSection>

          {/* Section 4: Missing Clauses */}
          <CollapsibleSection title="Missing Clauses" number={4}>
            <MissingClausesSection missingClauses={analysis.missing_clauses} />
          </CollapsibleSection>

          {/* Section 5: Full Suggested Revisions */}
          <CollapsibleSection title="Full Suggested Revisions" number={5}>
            <SuggestedRevisionsSection suggestedRevisions={analysis.suggested_revisions} />
          </CollapsibleSection>
        </div>

        {/* Footer Disclaimer */}
        <div className="mt-8 p-4 bg-gray-100 border border-gray-300 rounded-lg print-break-inside-avoid">
          <p className="text-xs text-gray-600 text-center leading-relaxed">
            <strong>Disclaimer:</strong> This tool is for informational purposes only and does not
            constitute legal advice. Always verify outputs with a qualified lawyer before relying on
            this analysis for any legal decisions.
          </p>
        </div>
      </div>
    </div>
  );
}
