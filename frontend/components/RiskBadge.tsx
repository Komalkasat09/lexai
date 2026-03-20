'use client';

interface RiskBadgeProps {
  level: 'high' | 'moderate' | 'standard' | 'low';
  size?: 'sm' | 'md';
}

const RISK_CONFIG = {
  high: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    border: 'border-red-300',
    label: 'High Risk',
    icon: '🔴',
  },
  moderate: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    border: 'border-yellow-300',
    label: 'Moderate',
    icon: '🟡',
  },
  standard: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-300',
    label: 'Standard',
    icon: '🟢',
  },
  low: {
    bg: 'bg-gray-100',
    text: 'text-gray-800',
    border: 'border-gray-300',
    label: 'Low Risk',
    icon: '⚪',
  },
};

export default function RiskBadge({ level, size = 'md' }: RiskBadgeProps) {
  const config = RISK_CONFIG[level];
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
