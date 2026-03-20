'use client';

import { useState } from 'react';

interface CitationChipProps {
  type: 'section' | 'case';
  text: string;
  onClick?: () => void;
}

export default function CitationChip({ type, text, onClick }: CitationChipProps) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium transition-colors ${
        type === 'section'
          ? 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
          : 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200'
      }`}
    >
      {text}
    </button>
  );
}
