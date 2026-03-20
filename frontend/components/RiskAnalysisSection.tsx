import { Risk, SuggestedRevision, RiskLevel } from "@/lib/types";

interface RiskAnalysisSectionProps {
  risks: Risk[];
  suggestedRevisions: SuggestedRevision[];
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

export default function RiskAnalysisSection({
  risks,
  suggestedRevisions,
}: RiskAnalysisSectionProps) {
  // Filter to show only moderate and high risks
  const significantRisks = (risks || []).filter(
    (risk) => risk?.risk_level === "moderate" || risk?.risk_level === "high"
  );

  // Create a map of heading to suggested revision
  const revisionMap = new Map<string, SuggestedRevision>();
  (suggestedRevisions || []).forEach((revision) => {
    if (revision?.clause_heading) {
      revisionMap.set(revision.clause_heading, revision);
    }
  });

  if (significantRisks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p className="text-lg">✓ No significant risks identified</p>
        <p className="text-sm mt-2">All clauses are at standard risk level.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {significantRisks.map((risk, index) => {
        const revision = revisionMap.get(risk?.heading || "");

        return (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-5 print-break-inside-avoid"
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-base font-semibold text-navy">{risk?.heading || "Untitled Risk"}</h3>
              <RiskBadge level={risk?.risk_level || "standard"} />
            </div>

            <p className="text-sm text-gray-700 leading-relaxed mb-4">
              {risk?.explanation || "No explanation provided."}
            </p>

            {risk?.risk_level === "high" && revision && (
              <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <svg
                    className="w-5 h-5 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                  <span className="text-sm font-semibold text-blue-900">
                    Suggested Revision
                  </span>
                </div>
                <p className="text-sm text-blue-800 leading-relaxed">
                  {revision?.revised_clause || ""}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
