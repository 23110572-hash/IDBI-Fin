import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchAlerts, runMonitor } from "../lib/api";
import { useAuth } from "../lib/store";
import type { Alert } from "../lib/types";

const SEV: Record<string, string> = {
  high: "border-red-500 bg-red-50",
  medium: "border-orange-400 bg-orange-50",
  low: "border-yellow-400 bg-yellow-50",
};

export default function AlertFeed() {
  const qc = useQueryClient();
  const role = useAuth((s) => s.role);
  const token = useAuth((s) => s.token);
  const { data: initial = [] } = useQuery({ queryKey: ["alerts"], queryFn: fetchAlerts });
  const [live, setLive] = useState<Alert[]>([]);
  const [wsState, setWsState] = useState<"connecting" | "open" | "closed">("connecting");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/api/ws/alerts`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setWsState("open");
    ws.onclose = () => setWsState("closed");
    ws.onerror = () => setWsState("closed");
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === "alert") setLive((l) => [msg.data, ...l]);
        if (msg.event === "snapshot" && Array.isArray(msg.data)) setLive(msg.data);
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [token]);

  const monitor = useMutation({
    mutationFn: () => runMonitor("daily_delta"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const merged: Alert[] = dedupe([...live, ...initial]);
  const canMonitor = role === "admin" || role === "credit_officer";

  return (
    <div className="space-y-4">
      <div className="card p-4 flex items-center gap-3">
        <h2 className="font-bold text-slate-700 flex-1">
          Alert Feed (Mode B — portfolio monitoring)
        </h2>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            wsState === "open" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
          }`}
        >
          ● live {wsState}
        </span>
        {canMonitor && (
          <button className="btn-primary text-sm" disabled={monitor.isPending} onClick={() => monitor.mutate()}>
            {monitor.isPending ? "Running…" : "Run daily monitor"}
          </button>
        )}
      </div>

      {monitor.data && (
        <div className="text-sm text-slate-500">
          Re-scored {monitor.data.borrowers_scored} borrowers · {monitor.data.alerts_created} new
          alerts.
        </div>
      )}

      {merged.length === 0 ? (
        <div className="card p-10 text-center text-slate-500">
          No alerts yet. Run the daily monitor after scoring borrowers to detect tier crossings and
          score drops.
        </div>
      ) : (
        <div className="space-y-2">
          {merged.map((a) => (
            <div key={a.alert_id} className={`card p-4 border-l-4 ${SEV[a.severity] ?? ""}`}>
              <div className="flex items-center justify-between">
                <div className="font-semibold text-slate-700">
                  <span className="uppercase text-xs text-slate-400 mr-2">{a.type}</span>
                  {a.message}
                </div>
                <Link to={`/borrower/${a.urn}`} className="text-sm text-indigo-600 hover:underline">
                  {a.urn}
                </Link>
              </div>
              <div className="text-sm text-slate-500 mt-1">→ {a.suggested_action}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function dedupe(alerts: Alert[]): Alert[] {
  const seen = new Set<string>();
  return alerts.filter((a) => (seen.has(a.alert_id) ? false : (seen.add(a.alert_id), true)));
}
