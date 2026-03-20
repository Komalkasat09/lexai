interface CaseCardProps {
  caseData: {
    name: string;
    citation: string;
    court: string;
    date: string;
    judges?: string[];
    summary: string;
    principle?: string;
    overruled?: boolean;
    overruled_by?: string;
  };
  onClick?: () => void;
}

export default function CaseCard({ caseData, onClick }: CaseCardProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-200 p-6 hover:border-[#2E5499] hover:shadow-md transition-all cursor-pointer"
      onClick={onClick}
    >
      {/* Overruled Warning */}
      {caseData.overruled && (
        <div className="mb-4 p-3 bg-red-50 rounded border-2 border-red-500">
          <div className="flex items-start gap-2">
            <span className="text-lg">⛔</span>
            <div>
              <p className="text-xs font-bold text-red-900 uppercase mb-1">Overruled</p>
              <p className="text-sm text-red-800">
                This judgment has been overruled
                {caseData.overruled_by && ` by ${caseData.overruled_by}`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Case Title */}
      <h3 className="text-lg font-semibold text-gray-900 mb-2" style={{ fontFamily: 'Georgia, serif' }}>
        {caseData.name}
      </h3>

      {/* Citation & Court */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-semibold rounded">
          {caseData.citation}
        </span>
        <span className="text-sm text-gray-600">{caseData.court}</span>
        <span className="text-sm text-gray-400">•</span>
        <span className="text-sm text-gray-600">{caseData.date}</span>
      </div>

      {/* Judges if available */}
      {caseData.judges && caseData.judges.length > 0 && (
        <p className="text-xs text-gray-500 mb-3">
          <span className="font-semibold">Bench:</span> {caseData.judges.join(', ')}
        </p>
      )}

      {/* Summary */}
      <p className="text-sm text-gray-700 leading-relaxed mb-4">{caseData.summary}</p>

      {/* Legal Principle */}
      {caseData.principle && (
        <div className="p-3 bg-blue-50 rounded border-l-4 border-blue-500 mb-4">
          <p className="text-xs font-semibold text-blue-900 mb-1">Legal Principle</p>
          <p className="text-sm text-blue-800" style={{ fontFamily: 'Georgia, serif' }}>
            {caseData.principle}
          </p>
        </div>
      )}

      {/* Footer */}
      <div className="pt-3 border-t border-gray-100">
        <button className="text-sm text-[#2E5499] hover:text-[#1F3864] font-medium">
          View Full Judgment →
        </button>
      </div>
    </div>
  );
}
