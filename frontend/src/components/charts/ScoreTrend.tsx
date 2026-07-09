import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryEntry } from "../../lib/types";

export default function ScoreTrend({ history }: { history: HistoryEntry[] }) {
  const data = history.map((h, i) => ({
    idx: i + 1,
    label: new Date(h.created_at).toLocaleDateString(),
    score: h.composite_score,
    mode: h.mode,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
        {/* tier boundaries */}
        <ReferenceLine y={75} stroke="#65a30d" strokeDasharray="2 2" />
        <ReferenceLine y={60} stroke="#ca8a04" strokeDasharray="2 2" />
        <ReferenceLine y={40} stroke="#ea580c" strokeDasharray="2 2" />
        <Tooltip formatter={(v: number) => v.toFixed(1)} />
        <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={2.5} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
