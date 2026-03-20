interface SectionCardProps {
  section: {
    section_number: string;
    title: string;
    act: string;
    full_text: string;
    simple_explanation: string;
    punishment?: string;
    bns_equivalent?: string;
    amendment_history?: Array<{
      year: number;
      description: string;
    }>;
  };
  onClick?: () => void;
}

export default function SectionCard({ section, onClick }: SectionCardProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-200 p-6 hover:border-[#2E5499] hover:shadow-md transition-all cursor-pointer"
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
              {section.section_number}
            </span>
            <span className="text-xs text-gray-500">{section.act}</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{section.title}</h3>
        </div>
      </div>

      {/* Simple Explanation */}
      <div className="mb-4">
        <p className="text-sm text-gray-700 leading-relaxed">{section.simple_explanation}</p>
      </div>

      {/* Punishment if exists */}
      {section.punishment && (
        <div className="mb-3 p-3 bg-red-50 rounded border border-red-200">
          <p className="text-xs font-semibold text-red-900 mb-1">Punishment</p>
          <p className="text-sm text-red-800">{section.punishment}</p>
        </div>
      )}

      {/* BNS Warning if exists */}
      {section.bns_equivalent && (
        <div className="mb-3 p-3 bg-amber-50 rounded border border-amber-300">
          <div className="flex items-start gap-2">
            <span className="text-lg">⚠️</span>
            <div className="flex-1">
              <p className="text-xs font-semibold text-amber-900 mb-1">BNS Transition</p>
              <p className="text-sm text-amber-800">
                Now codified as <span className="font-semibold">{section.bns_equivalent}</span>{' '}
                under Bharatiya Nyaya Sanhita, 2023
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div className="flex items-center gap-2">
          {section.amendment_history && section.amendment_history.length > 0 && (
            <span className="text-xs text-gray-500">
              📝 {section.amendment_history.length} amendment
              {section.amendment_history.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <button className="text-sm text-[#2E5499] hover:text-[#1F3864] font-medium">
          View Full Text →
        </button>
      </div>
    </div>
  );
}
