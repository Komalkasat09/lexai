'use client';

interface TopBarProps {
  title: string;
}

export default function TopBar({ title }: TopBarProps) {
  return (
    <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h2 className="text-xl font-semibold text-[#2C3E50]">{title}</h2>
        <span className="px-2 py-0.5 bg-[#C8A951] text-white text-xs font-medium rounded">
          Beta
        </span>
      </div>

      <button className="px-4 py-2 text-sm text-[#2E5499] hover:text-[#1F3864] hover:bg-gray-50 rounded-lg transition-colors">
        Send Feedback
      </button>
    </div>
  );
}
