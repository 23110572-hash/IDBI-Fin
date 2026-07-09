import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import type { Pillar } from "../../lib/types";

const SHORT: Record<string, string> = {
  cash_flow_stability: "Cash Flow",
  gst_compliance_revenue: "GST",
  business_stability: "Business",
  bureau_credit_history: "Bureau",
  macroeconomic_context: "Macro",
};

export default function SubScoreRadar({
  pillars,
  sectorAvg,
}: {
  pillars: Pillar[];
  sectorAvg?: Record<string, number>;
}) {
  const data = pillars.map((p) => ({
    pillar: SHORT[p.pillar] ?? p.label,
    borrower: p.sub_score,
    sector: sectorAvg?.[p.pillar] ?? 55,
    available: p.available,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 12, fill: "#475569" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} />
        <Radar name="Borrower" dataKey="borrower" stroke="#4f46e5" fill="#6366f1" fillOpacity={0.5} />
        <Radar name="Sector avg" dataKey="sector" stroke="#94a3b8" fill="#cbd5e1" fillOpacity={0.25} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Tooltip formatter={(v: number) => v.toFixed(1)} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
