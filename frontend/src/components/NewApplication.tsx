import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createConsent, scoreBorrower, type Identifiers } from "../lib/api";
import type { HealthCard, ScoreResponse } from "../lib/types";
import HealthCardView from "./HealthCardView";
import ElectricityUpload from "./ElectricityUpload";

const SAMPLE: Identifiers = {
  urn: "UDYAM-MH-03-1234567",
  pan: "ABCDE1234F",
  gstin: "27ABCDE1234F1Z5",
  business_name: "",
};

export default function NewApplication() {
  const qc = useQueryClient();
  const [form, setForm] = useState<Identifiers>(SAMPLE);
  const [consentGiven, setConsentGiven] = useState(false);
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [enrichedCard, setEnrichedCard] = useState<HealthCard | null>(null);

  const mutation = useMutation({
    mutationFn: async (ids: Identifiers) => {
      const consent = await createConsent(ids);
      return scoreBorrower(ids, consent.consent_id);
    },
    onSuccess: (data) => {
      setResult(data);
      setEnrichedCard(null);
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });

  function update(k: keyof Identifiers, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-lg font-bold">New MSME Assessment (Mode A — origination)</h2>
        <p className="text-sm text-slate-500 mt-1">
          Enter the applicant's identifiers and capture AA consent. The score is computed live: 8
          data sources are pulled in parallel, turned into a 65-feature vector, and run through the
          single XGBoost model — no pre-computed results.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
          <div>
            <label className="label">Udyam Registration Number (URN)</label>
            <input className="input" value={form.urn} onChange={(e) => update("urn", e.target.value)} />
          </div>
          <div>
            <label className="label">Business PAN</label>
            <input className="input" value={form.pan} onChange={(e) => update("pan", e.target.value)} />
          </div>
          <div>
            <label className="label">GSTIN (optional — NTC firms may lack it)</label>
            <input
              className="input"
              value={form.gstin ?? ""}
              onChange={(e) => update("gstin", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Business name</label>
            <input
              className="input"
              value={form.business_name ?? ""}
              onChange={(e) => update("business_name", e.target.value)}
            />
          </div>
        </div>

        <label className="flex items-start gap-2 mt-4 text-sm text-slate-600">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={consentGiven}
            onChange={(e) => setConsentGiven(e.target.checked)}
          />
          <span>
            The borrower consents (DPDP / AA Sahamati) to share GST, bank statement, EPFO and UPI
            data for credit assessment. Purpose-limited, time-bound (90 days), revocable.
          </span>
        </label>

        <div className="mt-4 flex items-center gap-3">
          <button
            className="btn-primary"
            disabled={!consentGiven || mutation.isPending}
            onClick={() => mutation.mutate(form)}
          >
            {mutation.isPending ? "Scoring…" : "Capture consent & score"}
          </button>
          {result && (
            <span className="text-sm text-slate-500">
              Scored in {result.latency_ms} ms · {result.score_id}
            </span>
          )}
          {mutation.isError && (
            <span className="text-sm text-red-600">
              {(mutation.error as any)?.response?.data?.detail?.message ||
                "Scoring failed (check inputs / model trained)."}
            </span>
          )}
        </div>
      </div>

      {result && (
        <div>
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-lg font-bold">
              Health Card — {result.business_name || result.urn}
            </h2>
            <span className="text-sm text-slate-400">{result.urn}</span>
          </div>
          <HealthCardView
            card={enrichedCard ?? result.health_card}
            scorecard={result.scorecard}
            dataQuality={result.data_quality}
          />

          <div className="mt-4">
            <ElectricityUpload
              identifiers={{ urn: result.urn, pan: form.pan, gstin: form.gstin }}
              baselineScore={result.health_card.composite_score}
              onEnriched={(card) => {
                setEnrichedCard(card);
                qc.invalidateQueries({ queryKey: ["portfolio"] });
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
