import type { Pillar } from "../lib/types";
import { scoreColor } from "../lib/tiers";

/** Shows each pillar's sub-score and the DYNAMICALLY RENORMALISED display weight. When a pillar has
 * no data (e.g. NTC -> empty Bureau) its weight is 0 and redistributed across present pillars — a
 * dashboard concern only; the model PD is unchanged. */
export default function PillarWeights({ pillars }: { pillars: Pillar[] }) {
  const renormalised = pillars.some((p) => !p.available && p.base_weight > 0);
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-slate-700">Pillars</h3>
        {renormalised && (
          <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full border border-amber-200">
            weights renormalised (missing pillar)
          </span>
        )}
      </div>
      <div className="space-y-3">
        {pillars.map((p) => (
          <div key={p.pillar} className={p.available ? "" : "opacity-60"}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{p.label}</span>
              <span className="text-slate-500">
                {p.available ? (
                  <>
                    <span className="font-semibold text-slate-800">{p.sub_score.toFixed(0)}</span>
                    <span className="mx-1">·</span>
                  </>
                ) : (
                  <span className="italic mr-1">no data · </span>
                )}
                <span title={`base ${p.base_weight}%`}>
                  {p.display_weight.toFixed(0)}%
                  {p.base_weight !== p.display_weight && (
                    <span className="text-slate-400"> (base {p.base_weight}%)</span>
                  )}
                </span>
              </span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${p.available ? p.sub_score : 0}%`,
                  backgroundColor: scoreColor(p.sub_score),
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
