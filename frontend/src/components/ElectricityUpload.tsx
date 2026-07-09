import { useState } from "react";
import { uploadElectricityBill, type Identifiers } from "../lib/api";
import type { HealthCard } from "../lib/types";

/**
 * Electricity bill upload -> OCR -> ASYNC enrichment (off the <30s origination path, per the
 * architecture). Shows the extracted units and the re-scored Health Card once the utility signal
 * folds into Business Stability.
 */
export default function ElectricityUpload({
  identifiers,
  baselineScore,
  onEnriched,
}: {
  identifiers: Identifiers;
  baselineScore: number;
  onEnriched: (card: HealthCard) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ocr, setOcr] = useState<Awaited<ReturnType<typeof uploadElectricityBill>>["ocr"] | null>(null);
  const [newScore, setNewScore] = useState<number | null>(null);

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await uploadElectricityBill(identifiers, file);
      setOcr(res.ocr);
      const card = res.enrichment?.health_card;
      if (card) {
        setNewScore(card.composite_score);
        onEnriched(card);
      } else if (res.enrichment?.composite_score != null) {
        setNewScore(res.enrichment.composite_score);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  const delta = newScore != null ? newScore - baselineScore : null;

  return (
    <div className="card p-5">
      <h3 className="font-semibold text-slate-700">
        Electricity bill <span className="text-xs font-normal text-slate-400">(async enrichment · off critical path)</span>
      </h3>
      <p className="text-sm text-slate-500 mt-1">
        Upload a recent power bill. OCR extracts units-consumed and the score is re-computed with the
        Utility / Business-Stability signal added. A sample bill lives in
        <code className="mx-1">data\raw_payloads\&lt;id&gt;\electricity_bill.txt</code>.
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".txt,.pdf,.png,.jpg,.jpeg"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <button className="btn-primary text-sm" disabled={!file || busy} onClick={submit}>
          {busy ? "Processing…" : "Upload & enrich"}
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      {ocr && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <Field label="Units consumed" value={ocr.units_consumed_kwh != null ? `${ocr.units_consumed_kwh} kWh` : "—"} />
          <Field label="Sanctioned load" value={ocr.sanctioned_load_kw != null ? `${ocr.sanctioned_load_kw} kW` : "—"} />
          <Field label="Bill amount" value={ocr.bill_amount != null ? `₹${ocr.bill_amount.toLocaleString()}` : "—"} />
          <Field label="OCR engine" value={ocr.engine} />
        </div>
      )}

      {newScore != null && (
        <div className="mt-3 text-sm">
          <span className="text-slate-500">Score after enrichment: </span>
          <span className="font-semibold text-slate-800">{newScore.toFixed(0)}</span>
          {delta != null && (
            <span className={`ml-2 font-medium ${delta >= 0 ? "text-green-600" : "text-red-600"}`}>
              ({delta >= 0 ? "+" : ""}
              {delta.toFixed(1)} vs origination)
            </span>
          )}
          <span className="text-slate-400"> — the card above has been updated.</span>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-medium text-slate-700">{value}</div>
    </div>
  );
}
