import { ContractOverview } from "@/lib/types";

interface ContractOverviewSectionProps {
  overview: ContractOverview;
}

export default function ContractOverviewSection({ overview }: ContractOverviewSectionProps) {
  const fields = [
    { label: "Contract Type", value: overview?.contract_type },
    { label: "Parties", value: overview?.parties?.join(", ") },
    { label: "Governing Law", value: overview?.governing_law },
    { label: "Jurisdiction", value: overview?.jurisdiction },
    { label: "Effective Date", value: overview?.effective_date },
    { label: "Duration", value: overview?.duration },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {fields.map((field, index) => (
        <div key={index} className="border-b border-gray-100 pb-3">
          <dt className="text-sm font-medium text-gray-600 mb-1">{field.label}</dt>
          <dd className="text-base text-navy font-medium">{field.value || "—"}</dd>
        </div>
      ))}
    </div>
  );
}
