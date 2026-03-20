"use client";

import React, { useState } from "react";
import { Clause, Risk, RiskLevel } from "@/lib/types";

interface ClauseSummarySectionProps {
  clauses: Clause[];
  risks: Risk[];
}

function RiskBadge({ level }: { level: RiskLevel }) {
  const styles = {
    standard: "bg-green-100 text-green-800 border-green-200",
    moderate: "bg-amber-100 text-amber-800 border-amber-200",
    high: "bg-red-100 text-red-800 border-red-200",
  };

  const labels = {
    standard: "🟢 Standard",
    moderate: "🟡 Moderate",
    high: "🔴 High",
  };

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${styles[level]}`}
    >
      {labels[level]}
    </span>
  );
}

export default function ClauseSummarySection({ clauses, risks }: ClauseSummarySectionProps) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Create a map of clause heading to risk level
  const riskMap = new Map<string, RiskLevel>();
  risks?.forEach((risk) => {
    if (risk.heading) {
      riskMap.set(risk.heading, risk.risk_level);
    }
  });

  // Handle empty or undefined clauses
  if (!clauses || clauses.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No clauses found in the contract.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b-2 border-gray-200">
            <th className="text-left py-3 px-4 text-sm font-semibold text-navy">Clause</th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-navy">Type</th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-navy">Risk Level</th>
          </tr>
        </thead>
        <tbody>
          {clauses.map((clause, index) => {
            const riskLevel = riskMap.get(clause?.heading || "") || "standard";
            const isExpanded = expandedRow === index;

            return (
              <React.Fragment key={index}>
                <tr
                  onClick={() => setExpandedRow(isExpanded ? null : index)}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors no-print"
                >
                  <td className="py-3 px-4 text-sm font-medium text-navy">
                    {clause?.heading || "Untitled Clause"}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-700">{clause?.type || "—"}</td>
                  <td className="py-3 px-4 text-sm">
                    <RiskBadge level={riskLevel} />
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-gray-50 no-print">
                    <td colSpan={3} className="py-4 px-4">
                      <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {clause?.text || "No content available"}
                      </div>
                    </td>
                  </tr>
                )}
                
                {/* Print version - always show all content */}
                <tr className="hidden print:table-row border-b border-gray-100">
                  <td className="py-3 px-4 text-sm font-medium text-navy">
                    {clause?.heading || "Untitled Clause"}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-700">{clause?.type || "—"}</td>
                  <td className="py-3 px-4 text-sm">
                    <RiskBadge level={riskLevel} />
                  </td>
                </tr>
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
