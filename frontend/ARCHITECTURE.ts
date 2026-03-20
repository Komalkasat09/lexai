/**
 * COMPONENT ARCHITECTURE REFERENCE
 * Quick visual guide to the component tree and data flow
 */

/**
 * PAGE STRUCTURE
 * ================
 * 
 * app/page.tsx (Main Page)
 *   - State Management:
 *     - isAnalyzing: boolean
 *     - analysis: ContractAnalysis | null
 *     - filename: string
 *     - error: string | null
 * 
 *   - Conditional Rendering:
 *     1. If error → Show error modal
 *     2. If analysis → Show Results component
 *     3. Otherwise → Show Upload component
 */

/**
 * UPLOAD FLOW
 * ============
 * 
 * Upload Component
 *   ├── Drag & Drop Zone
 *   ├── File Input (hidden)
 *   ├── File Validation
 *   │   ├── Type check: .pdf, .docx
 *   │   └── Size check: max 10MB
 *   ├── Loading Spinner (when analyzing)
 *   └── Analyze Button
 *       └── Calls: handleFileSelect(file)
 *           └── API: analyzeContract(file)
 *               └── POST /api/analyze-contract
 */

/**
 * RESULTS FLOW
 * =============
 * 
 * Results Component
 *   ├── Header
 *   │   ├── Title & Filename
 *   │   └── Action Buttons
 *   │       ├── Download Report (window.print)
 *   │       └── New Analysis
 *   │
 *   ├── Section 1: Contract Overview
 *   │   └── ContractOverviewSection
 *   │       └── Grid of key-value pairs
 *   │
 *   ├── Section 2: Clause Summary
 *   │   └── ClauseSummarySection
 *   │       ├── Table Headers
 *   │       └── Expandable Rows
 *   │           ├── Clause heading
 *   │           ├── Clause type
 *   │           ├── Risk badge
 *   │           └── Full text (on expand)
 *   │
 *   ├── Section 3: Risk Analysis
 *   │   └── RiskAnalysisSection
 *   │       └── Risk Cards (moderate + high only)
 *   │           ├── Heading
 *   │           ├── Risk badge
 *   │           ├── Explanation
 *   │           └── Suggested revision (high risk only)
 *   │
 *   ├── Section 4: Missing Clauses
 *   │   └── MissingClausesSection
 *   │       └── Warning Cards
 *   │           ├── ⚠️ Icon
 *   │           ├── Clause name
 *   │           └── Explanation (hardcoded)
 *   │
 *   ├── Section 5: Suggested Revisions
 *   │   └── SuggestedRevisionsSection
 *   │       └── Revision Cards
 *   │           ├── Current Box (grey)
 *   │           └── Suggested Box (blue)
 *   │               └── Copy Button
 *   │
 *   └── Footer Disclaimer
 */

/**
 * SHARED COMPONENTS
 * ==================
 * 
 * CollapsibleSection
 *   Props:
 *     - title: string
 *     - number: 1-5
 *     - children: ReactNode
 *     - defaultOpen?: boolean
 *   
 *   Features:
 *     - Click header to expand/collapse
 *     - Numbered badge
 *     - Print: always expanded
 */

/**
 * TYPE HIERARCHY
 * ===============
 * 
 * ContractAnalysis {
 *   overview: ContractOverview
 *   clauses: Clause[]
 *   risks: Risk[]
 *   missing_clauses: string[]
 *   suggested_revisions: SuggestedRevision[]
 * }
 * 
 * ContractOverview {
 *   contract_type, parties[], governing_law,
 *   jurisdiction, effective_date, duration
 * }
 * 
 * Clause {
 *   heading, text, type
 * }
 * 
 * Risk {
 *   heading, risk_level: RiskLevel, explanation
 * }
 * 
 * RiskLevel = "standard" | "moderate" | "high"
 * 
 * SuggestedRevision {
 *   heading, original, revised
 * }
 */

/**
 * API FLOW
 * =========
 * 
 * Client                    API Client              Backend
 *   |                          |                       |
 *   |-- handleFileSelect() --->|                       |
 *   |                          |                       |
 *   |                          |-- FormData with file->|
 *   |                          |                       |
 *   |                          |                   [Analysis]
 *   |                          |                       |
 *   |                          |<-- JSON response -----|
 *   |                          |                       |
 *   |<-- ContractAnalysis -----|                       |
 *   |                          |                       |
 *   |-- setAnalysis() -------->|                       |
 *   |                          |                       |
 *   |-- Render Results ------->|                       |
 * 
 * Error Handling:
 *   - File validation errors (local)
 *   - Network errors (APIError)
 *   - Backend errors (APIError with status)
 *   - Invalid response format (APIError)
 */

/**
 * STYLING SYSTEM
 * ===============
 * 
 * Colors (defined in globals.css):
 *   --foreground: #1F3864  (Navy - headings)
 *   --accent: #2E5499      (Blue - buttons, links)
 *   --background: #ffffff  (White)
 * 
 * Tailwind Classes:
 *   text-navy   → #1F3864
 *   text-accent → #2E5499
 *   bg-accent   → #2E5499
 * 
 * Risk Badge Colors:
 *   standard  → green (bg-green-100 text-green-800)
 *   moderate  → amber (bg-amber-100 text-amber-800)
 *   high      → red (bg-red-100 text-red-800)
 * 
 * Print Classes:
 *   .no-print               → hidden in print
 *   .print-break-inside-avoid → keep together
 *   .print-break-before     → page break before
 */

/**
 * FILE ORGANIZATION
 * ==================
 * 
 * app/
 *   globals.css     → Design tokens, print CSS
 *   layout.tsx      → Inter font, metadata
 *   page.tsx        → Main logic, state, routing
 * 
 * components/
 *   Upload.tsx                      → Upload UI
 *   Results.tsx                     → Results container
 *   CollapsibleSection.tsx          → Shared wrapper
 *   ContractOverviewSection.tsx     → Section 1
 *   ClauseSummarySection.tsx        → Section 2
 *   RiskAnalysisSection.tsx         → Section 3
 *   MissingClausesSection.tsx       → Section 4
 *   SuggestedRevisionsSection.tsx   → Section 5
 * 
 * lib/
 *   types.ts        → TypeScript interfaces
 *   api.ts          → API client functions
 */

/**
 * KEY FEATURES CHECKLIST
 * =======================
 * 
 * ✅ File Upload
 *   - Drag and drop
 *   - File type validation
 *   - Size validation
 *   - Loading states
 * 
 * ✅ Analysis Display
 *   - 5 collapsible sections
 *   - Color-coded risk levels
 *   - Expandable table rows
 *   - Copy to clipboard
 * 
 * ✅ Export
 *   - Print to PDF
 *   - Clean print layout
 *   - All sections expanded
 *   - No interactive elements
 * 
 * ✅ Error Handling
 *   - Network errors
 *   - Backend errors
 *   - Validation errors
 *   - User-friendly messages
 * 
 * ✅ Design
 *   - Professional legal theme
 *   - Mobile responsive
 *   - Inter font
 *   - Navy/blue color scheme
 *   - No flashy animations
 */

export {}; // Make this a module
