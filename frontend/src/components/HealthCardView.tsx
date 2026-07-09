import type { HealthCard, ScorecardSnapshot, DataQuality } from "../lib/types";
import { tierStyle, SOURCE_LABELS } from "../lib/tiers";
import PillarWeights from "./PillarWeights";
import SubScoreRadar from "./charts/SubScoreRadar";
import ShapForcePlot from "./charts/ShapForcePlot";

export default function HealthCardView({
  card,
  scorecard,
  dataQuality,
}: {
  card: HealthCard;
  scorecard?: ScorecardSnapshot | null;
  dataQuality?: DataQuality | null;
}) {
  const t = tierStyle(card.tier);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Composite + tier */}
      <div className="card p-5 flex flex-col items-center justify-center">
        <div className="text-sm text-slate-500">Composite Health Score</div>
        <div className="text-6xl font-bold mt-1" style={{ color: t.color }}>
          {card.composite_score.toFixed(0)}
        </div>
        <div className={`mt-2 px-3 py-1 rounded-full text-sm font-semibold ${t.bg} ${t.text}`}>
          {card.tier_label}
        </div>
        <div className="text-xs text-slate-500 mt-3 text-center">{card.action}</div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 mt-4 text-xs text-slate-500">
          <div>PD</div><div className="text-right font-medium text-slate-700">{(card.pd * 100).toFixed(1)}%</div>
          <div>Confidence</div><div className="text-right font-medium text-slate-700">{(card.confidence * 100).toFixed(0)}%</div>
          <div>Segment</div><div className="text-right font-medium text-slate-700 capitalize">{card.segment_label.replace("_", " ")}</div>
        </div>
        <div className="text-[10px] text-slate-400 mt-3">{card.model_version}</div>
      </div>

      {/* Pillars w/ renormalisation */}
      <div className="card p-5">
        <PillarWeights pillars={card.pillars} />
      </div>

      {/* Radar */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-700 mb-2">Sub-scores vs sector</h3>
        <SubScoreRadar pillars={card.pillars} />
      </div>

      {/* Reason codes */}
      <div className="card p-5 lg:col-span-2">
        <h3 className="font-semibold text-slate-700 mb-3">Top reason codes (SHAP)</h3>
        <div className="space-y-2">
          {card.reason_codes.map((r) => (
            <div key={r.feature} className="flex items-center gap-3 text-sm">
              <span
                className={`w-2 h-2 rounded-full ${
                  r.impact === "negative" ? "bg-red-500" : "bg-blue-500"
                }`}
              />
              <span className="font-medium text-slate-700 w-56 truncate" title={r.feature}>
                {r.feature}
              </span>
              <span className="text-slate-500 flex-1 truncate">{r.label}</span>
              {r.actionable && (
                <span className="text-[10px] bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded">
                  actionable
                </span>
              )}
              <span
                className={`text-xs font-mono ${
                  r.impact === "negative" ? "text-red-600" : "text-blue-600"
                }`}
              >
                {r.shap > 0 ? "+" : ""}
                {r.shap.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-4">
          <ShapForcePlot reasons={card.reason_codes} />
        </div>
      </div>

      {/* Data sources + WOE scorecard */}
      <div className="card p-5 space-y-4">
        <div>
          <h3 className="font-semibold text-slate-700 mb-2">Data sources</h3>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(card.available_sources).map(([src, ok]) => (
              <span
                key={src}
                className={`text-xs px-2 py-0.5 rounded-full border ${
                  ok
                    ? "bg-green-50 text-green-700 border-green-200"
                    : "bg-slate-50 text-slate-400 border-slate-200 line-through"
                }`}
              >
                {SOURCE_LABELS[src] ?? src}
              </span>
            ))}
          </div>
          {dataQuality && (
            <div className="text-xs text-slate-500 mt-2">
              Feature coverage: {(dataQuality.feature_coverage * 100).toFixed(0)}% ·{" "}
              {dataQuality.passed ? "DQ gate passed" : "DQ gate failed"}
            </div>
          )}
        </div>

        {scorecard && (
          <div>
            <h3 className="font-semibold text-slate-700 mb-1">
              WOE Scorecard <span className="text-xs font-normal text-slate-400">(parallel · regulator view)</span>
            </h3>
            <p className="text-[11px] text-slate-500 mb-2">{scorecard.note}</p>
            <div className="max-h-40 overflow-auto border border-slate-100 rounded-lg">
              <table className="w-full text-[11px]">
                <thead className="bg-slate-50 sticky top-0">
                  <tr className="text-slate-500">
                    <th className="text-left px-2 py-1">Variable</th>
                    <th className="text-left px-2 py-1">Bin</th>
                    <th className="text-right px-2 py-1">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {scorecard.points_table.slice(0, 20).map((row, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-2 py-1 text-slate-600">{String(row["Variable"] ?? "")}</td>
                      <td className="px-2 py-1 text-slate-400">{String(row["Bin"] ?? "")}</td>
                      <td className="px-2 py-1 text-right font-mono">
                        {row["Points"] != null ? Number(row["Points"]).toFixed(1) : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
