import { MissingClause } from "@/lib/types";

interface MissingClausesSectionProps {
  missingClauses: MissingClause[];
}

// Hardcoded explanations for common missing clauses
const clauseExplanations: Record<string, string> = {
  "Arbitration": "Essential for resolving disputes outside court, reducing litigation costs and time.",
  "Indemnity": "Protects parties from liability arising from third-party claims or losses.",
  "Force Majeure": "Excuses performance during unforeseeable circumstances beyond parties' control.",
  "Confidentiality": "Prevents unauthorized disclosure of sensitive business information.",
  "Termination": "Defines conditions and procedures for ending the contractual relationship.",
  "Limitation of Liability": "Caps potential damages to protect parties from excessive financial exposure.",
  "Intellectual Property": "Clarifies ownership and usage rights of IP created during the agreement.",
  "Data Protection": "Ensures compliance with privacy laws when handling personal data.",
  "Notice": "Establishes formal communication channels for legal notices and correspondence.",
  "Governing Law": "Specifies which jurisdiction's laws apply to interpret the contract.",
  "Severability": "Ensures remaining provisions survive if any clause is deemed invalid.",
  "Amendment": "Defines process for making changes to the contract after execution.",
  "Assignment": "Restricts or permits transfer of contractual rights to third parties.",
  "Waiver": "Clarifies that failure to enforce a right doesn't constitute waiver of that right.",
  "Payment Terms": "Specifies amounts, schedules, and methods for financial obligations.",
  "Warranties": "Establishes representations and guarantees made by each party.",
  "Compliance": "Ensures adherence to applicable laws and regulatory requirements.",
};

export default function MissingClausesSection({ missingClauses }: MissingClausesSectionProps) {
  if (!missingClauses || missingClauses.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p className="text-lg">✓ No critical clauses missing</p>
        <p className="text-sm mt-2">All standard clauses appear to be present.</p>
      </div>
    );
  }

  // Badge colors by importance
  const importanceBadge = (importance: string) => {
    const styles = {
      critical: "bg-red-100 text-red-800 border-red-300",
      recommended: "bg-amber-100 text-amber-800 border-amber-300",
      optional: "bg-blue-100 text-blue-800 border-blue-300",
    };
    const labels = {
      critical: "Critical",
      recommended: "Recommended",
      optional: "Optional",
    };
    return (
      <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${styles[importance as keyof typeof styles] || styles.recommended}`}>
        {labels[importance as keyof typeof labels] || importance}
      </span>
    );
  };

  return (
    <div className="space-y-3">
      {missingClauses.map((clause, index) => (
        <div
          key={index}
          className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg print-break-inside-avoid"
        >
          <span className="text-2xl flex-shrink-0">⚠️</span>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-semibold text-navy">{clause?.clause_type || "Unknown Clause"}</h4>
              {clause?.importance && importanceBadge(clause.importance)}
            </div>
            <p className="text-sm text-gray-700">
              {clause?.reason || clauseExplanations[clause?.clause_type] || 
                "This clause is typically included to protect parties' interests and clarify obligations."}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
