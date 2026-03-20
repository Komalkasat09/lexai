"use client";

import { useState, ReactNode } from "react";

interface CollapsibleSectionProps {
  title: string;
  number: number;
  children: ReactNode;
  defaultOpen?: boolean;
}

export default function CollapsibleSection({
  title,
  number,
  children,
  defaultOpen = true,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden print-break-inside-avoid">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between text-left no-print"
      >
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-accent text-white text-sm font-semibold">
            {number}
          </span>
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
        </div>
        <svg
          className={`w-5 h-5 text-navy transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      
      {/* Print version always shows section header */}
      <div className="hidden print:block px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-accent text-white text-sm font-semibold">
            {number}
          </span>
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
        </div>
      </div>

      {isOpen && <div className="px-6 py-5 bg-white">{children}</div>}
      
      {/* Print version always shows content */}
      <div className="hidden print:block px-6 py-5 bg-white">{children}</div>
    </div>
  );
}
