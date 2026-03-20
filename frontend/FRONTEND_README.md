# Contract Review Assistant - Frontend

Professional Next.js frontend for AI-powered contract analysis, designed for Indian commercial lawyers.

## 🎨 Design System

- **Primary Color (Navy):** `#1F3864` - Used for headings and important text
- **Accent Color:** `#2E5499` - Used for buttons, links, and highlights
- **Background:** White (`#ffffff`)
- **Typography:** Inter (Google Fonts)
- **Style:** Clean, minimal, trustworthy - designed for legal professionals

## 📁 Project Structure

```
frontend/
├── app/
│   ├── globals.css          # Global styles, design tokens, print CSS
│   ├── layout.tsx            # Root layout with Inter font
│   └── page.tsx              # Main page with upload & results logic
├── components/
│   ├── Upload.tsx            # File upload interface with drag-and-drop
│   ├── Results.tsx           # Main results container with export
│   ├── CollapsibleSection.tsx # Reusable collapsible section wrapper
│   ├── ContractOverviewSection.tsx
│   ├── ClauseSummarySection.tsx
│   ├── RiskAnalysisSection.tsx
│   ├── MissingClausesSection.tsx
│   └── SuggestedRevisionsSection.tsx
└── lib/
    ├── types.ts              # TypeScript interfaces for API responses
    └── api.ts                # API client for backend communication
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend server running at `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Backend Configuration

The frontend expects the FastAPI backend at `http://localhost:8000` by default.

To use a different URL, set the environment variable:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://your-backend-url:8000
```

### Backend CORS Setup

Ensure your FastAPI backend has CORS middleware configured:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📋 Features

### Upload Screen
- ✅ Drag-and-drop file upload
- ✅ File type validation (PDF, DOCX only)
- ✅ File size validation (max 10MB)
- ✅ Loading state with spinner
- ✅ Legal disclaimer

### Results Screen

**5 Collapsible Sections:**

1. **Contract Overview** - Key contract details (type, parties, dates, jurisdiction)
2. **Clause Summary** - Interactive table with all clauses, types, and risk levels
3. **Risk Analysis** - Detailed analysis of moderate and high-risk clauses
4. **Missing Clauses** - List of recommended clauses not found in the contract
5. **Suggested Revisions** - Side-by-side comparison with copy button

### Interactive Features
- ✅ Expandable clause rows in summary table
- ✅ Color-coded risk badges (🟢 Standard, 🟡 Moderate, 🔴 High)
- ✅ Copy-to-clipboard for suggested revisions
- ✅ Collapsible sections for better organization
- ✅ Export to PDF via browser print
- ✅ Mobile responsive design

## 🖨️ PDF Export

The "Download Report as PDF" button uses `window.print()` with custom print CSS:

- All sections automatically expand in print view
- Clean layout without interactive elements
- Proper page breaks to avoid content splitting
- Color-accurate for risk indicators

**How to use:**
1. Click "Download Report as PDF"
2. Browser print dialog opens
3. Select "Save as PDF" as destination
4. Click Save

## 🎨 Component Overview

### Upload Component
**File:** `components/Upload.tsx`

Handles file selection and validation:
- Drag-and-drop zone
- File type checking (PDF/DOCX)
- Size validation (10MB max)
- Loading state during analysis
- Error handling

### Results Component
**File:** `components/Results.tsx`

Main results container:
- Header with filename and export button
- 5 collapsible analysis sections
- Footer disclaimer
- Print-friendly layout

### Section Components

**CollapsibleSection** - Reusable wrapper for each section with expand/collapse

**ContractOverviewSection** - Grid layout of contract metadata

**ClauseSummarySection** - Interactive table with expandable rows

**RiskAnalysisSection** - Cards for moderate/high risks with suggested revisions

**MissingClausesSection** - Warning cards for missing clauses with explanations

**SuggestedRevisionsSection** - Side-by-side original vs revised with copy button

## 🔧 API Integration

### API Client
**File:** `lib/api.ts`

```typescript
// Analyze contract
const analysis = await analyzeContract(file);

// Check backend health
const isHealthy = await checkHealth();
```

### Type Definitions
**File:** `lib/types.ts`

Complete TypeScript interfaces matching the backend response structure:
- `ContractAnalysis`
- `ContractOverview`
- `Clause`
- `Risk`
- `SuggestedRevision`
- `RiskLevel`

## 🎯 Error Handling

The app handles these error scenarios:
- ❌ Backend server not running
- ❌ Invalid file type
- ❌ File too large (>10MB)
- ❌ Network errors
- ❌ Invalid API response
- ❌ Analysis failures

All errors show a clean error modal with retry option.

## 🌈 Risk Level Colors

```typescript
Standard Risk:  🟢 Green  (#10b981)
Moderate Risk:  🟡 Amber  (#f59e0b)
High Risk:      🔴 Red    (#ef4444)
```

## 📱 Responsive Design

- Mobile-first approach with Tailwind CSS
- Breakpoints: `sm` (640px), `md` (768px), `lg` (1024px)
- Touch-friendly interactions
- Optimized table layout for small screens

## 🛠️ Development

### Build for Production

```bash
npm run build
npm run start
```

### Linting

```bash
npm run lint
```

### Type Checking

TypeScript is configured with strict mode. The project uses:
- Next.js 14 with App Router
- React 19
- TypeScript 5
- Tailwind CSS 4

## 📝 Customization

### Colors

Edit `app/globals.css`:

```css
:root {
  --foreground: #1F3864;  /* Navy text */
  --accent: #2E5499;      /* Accent color */
}
```

### Fonts

Edit `app/layout.tsx`:

```typescript
import { Inter } from "next/font/google";
// Replace with your preferred Google Font
```

### API Endpoint

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://your-backend-url:8000
```

## 🚨 Disclaimer

The disclaimer appears in two places:
1. Upload screen (below the upload button)
2. Results screen (footer of analysis report)

Text can be customized in `components/Upload.tsx` and `components/Results.tsx`.

## 📄 License

This project is built for educational and professional use in legal contract analysis.

---

**Need help?** Check that:
1. Backend is running at `http://localhost:8000`
2. Backend CORS is configured correctly
3. File is PDF or DOCX and under 10MB
4. Node.js version is 18 or higher
