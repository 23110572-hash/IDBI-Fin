import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchPortfolio } from "../lib/api";
import { tierStyle } from "../lib/tiers";
import type { PortfolioBorrower } from "../lib/types";

type SortKey = "score_desc" | "score_asc" | "recent";

export default function PortfolioHeatMap() {
  const navigate = useNavigate();
  const { data = [], isLoading } = useQuery({ queryKey: ["portfolio"], queryFn: fetchPortfolio });
  const [sort, setSort] = useState<SortKey>("recent");
  const [tierFilter, setTierFilter] = useState<string>("all");

  const sorted = useMemo(() => {
    let list = [...data];
    if (tierFilter !== "all") list = list.filter((b) => b.tier === tierFilter);
    if (sort === "score_desc") list.sort((a, b) => b.composite_score - a.composite_score);
    else if (sort === "score_asc") list.sort((a, b) => a.composite_score - b.composite_score);
    else list.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
    return list;
  }, [data, sort, tierFilter]);

  const watchList = data.filter((b) => ["watch", "risk", "high_risk"].includes(b.tier));
  const opportunity = data.filter((b) => b.tier === "fair");

  if (isLoading) return <div className="text-slate-500">Loading portfolio…</div>;

  if (!data.length)
    return (
      <div className="card p-10 text-center text-slate-500">
        <div className="text-lg font-semibold text-slate-700">Portfolio is empty</div>
        <p className="mt-2 text-sm">
          This console live-scores on demand. Run a{" "}
          <span className="text-indigo-600 font-medium">New Assessment</span> and scored borrowers
          appear here.
        </p>
      </div>
    );

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat label="Borrowers assessed" value={data.length} />
        <Stat label="Watch-list (Watch/Risk)" value={watchList.length} tone="text-orange-600" />
        <Stat label="Opportunity (Fair — reviewable)" value={opportunity.length} tone="text-yellow-600" />
      </div>

      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h2 className="font-bold text-slate-700 flex-1">Portfolio Heat Map</h2>
          <select className="input w-auto text-sm" value={tierFilter} onChange={(e) => setTierFilter(e.target.value)}>
            <option value="all">All tiers</option>
            <option value="excellent">Excellent</option>
            <option value="good">Good</option>
            <option value="fair">Fair</option>
            <option value="watch">Watch</option>
            <option value="risk">Risk</option>
            <option value="high_risk">High Risk</option>
          </select>
          <select className="input w-auto text-sm" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="recent">Most recent</option>
            <option value="score_desc">Score high → low</option>
            <option value="score_asc">Score low → high</option>
          </select>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {sorted.map((b) => (
            <BorrowerCard key={b.urn} b={b} onClick={() => navigate(`/borrower/${b.urn}`)} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="card p-4">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${tone ?? "text-slate-800"}`}>{value}</div>
    </div>
  );
}

function BorrowerCard({ b, onClick }: { b: PortfolioBorrower; onClick: () => void }) {
  const t = tierStyle(b.tier);
  return (
    <button
      onClick={onClick}
      className={`text-left rounded-xl p-3 border-2 hover:shadow-md transition-shadow ${t.bg}`}
      style={{ borderColor: t.color }}
    >
      <div className="text-2xl font-bold" style={{ color: t.color }}>
        {b.composite_score.toFixed(0)}
      </div>
      <div className={`text-[11px] font-semibold ${t.text}`}>{b.tier_label}</div>
      <div className="text-xs font-medium text-slate-700 mt-1 truncate">
        {b.business_name || b.urn}
      </div>
      <div className="text-[10px] text-slate-500 capitalize">
        {b.segment} · {b.sector?.replace("_", " ")}
      </div>
    </button>
  );
}
