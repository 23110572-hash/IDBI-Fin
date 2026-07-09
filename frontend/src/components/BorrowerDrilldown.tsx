import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { fetchBorrower, fetchAlerts } from "../lib/api";
import HealthCardView from "./HealthCardView";
import ScoreTrend from "./charts/ScoreTrend";

export default function BorrowerDrilldown() {
  const { urn = "" } = useParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["borrower", urn],
    queryFn: () => fetchBorrower(urn),
  });
  const { data: alerts = [] } = useQuery({ queryKey: ["alerts"], queryFn: fetchAlerts });

  if (isLoading) return <div className="text-slate-500">Loading borrower…</div>;
  if (isError || !data) return <div className="text-slate-500">No data for {urn}.</div>;

  const latest = data.latest;
  const borrowerAlerts = alerts.filter((a) => a.urn === urn);

  // reconstruct a HealthCard shape from the latest history entry
  const card = {
    pd: latest.pd,
    composite_score: latest.composite_score,
    tier: latest.tier,
    tier_label: latest.tier_label,
    action: "",
    segment_label: "",
    confidence: 0,
    pillars: latest.pillars,
    reason_codes: latest.reason_codes,
    model_version: latest.model_version,
    available_sources: latest.available_sources,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/portfolio" className="btn-ghost text-sm">
          ← Portfolio
        </Link>
        <h2 className="text-lg font-bold">{urn}</h2>
        <span className="text-sm text-slate-400">{data.history.length} assessments</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-5 lg:col-span-2">
          <h3 className="font-semibold text-slate-700 mb-2">Score trend (assessment history)</h3>
          <ScoreTrend history={data.history} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-700 mb-2">Alert history (90 days)</h3>
          {borrowerAlerts.length === 0 ? (
            <div className="text-sm text-slate-400">No alerts.</div>
          ) : (
            <div className="space-y-2">
              {borrowerAlerts.map((a) => (
                <div key={a.alert_id} className="text-sm border-l-2 border-orange-400 pl-2">
                  <div className="font-medium text-slate-700">{a.message}</div>
                  <div className="text-xs text-slate-500">{a.suggested_action}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <HealthCardView card={card} />

      <div className="card p-5">
        <h3 className="font-semibold text-slate-700 mb-2">Raw feature snapshot (latest)</h3>
        <p className="text-xs text-slate-500 mb-3">
          Reproducibility: every score is stored with its full 65-feature snapshot + model version
          in the append-only ledger. Showing the SHAP-ranked drivers below.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
          {latest.reason_codes.map((r) => (
            <div key={r.feature} className="flex justify-between border-b border-slate-100 py-1">
              <span className="text-slate-500 truncate mr-2" title={r.feature}>
                {r.feature}
              </span>
              <span className="font-medium text-slate-700">
                {r.value != null ? r.value : "—"} {r.unit}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
