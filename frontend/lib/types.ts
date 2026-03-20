/**
 * TypeScript types for Contract Analysis API
 * These match the FastAPI backend response structure exactly
 */

export interface ContractOverview {
  contract_type?: string;
  parties?: string[];
  governing_law?: string;
  jurisdiction?: string;
  effective_date?: string;
  duration?: string;
}

export interface Clause {
  heading: string;
  text: string;
  type: string;
}

export type RiskLevel = "standard" | "moderate" | "high";

export interface Risk {
  heading: string;
  risk_level: RiskLevel;
  explanation: string;
}

export interface SuggestedRevision {
  clause_number: number;
  clause_heading: string;
  original_issue: string;
  revised_clause: string;
  key_changes: string;
}

export interface MissingClause {
  clause_type: string;
  importance: "critical" | "recommended" | "optional";
  reason: string;
}

export interface ContractAnalysis {
  overview: ContractOverview;
  clauses: Clause[];
  risks: Risk[];
  missing_clauses: MissingClause[];
  suggested_revisions: SuggestedRevision[];
}
