# Runbook — MSME Financial Health Card

End-to-end operating guide for the demo and local development. The trained model is already bundled
in `backend/model_artifacts/` — there is nothing to train to run the app.

---

## Run the app

```bat
start.bat
```

One command. The first run installs dependencies (creates `ml\.venv`, installs the backend + its
runtime ML deps, and runs `npm install`); every run launches the **backend**
(http://localhost:8000, docs at `/docs`) and the **frontend** (http://localhost:5173) and opens the
dashboard in Chrome. Sign in as `rm / rm123!`. The backend serves the bundled model directly —
nothing to train. Requires Python 3.11+ and Node 18+.

---

## Demo script (live-score on demand — nothing pre-baked)

1. Open http://localhost:5173 and **sign in** as `rm / rm123!`.
2. Go to **New Assessment**. Enter identifiers (a sample is pre-filled):
   - URN `UDYAM-MH-03-1234567`, PAN `ABCDE1234F`, GSTIN `27ABCDE1234F1Z5`.
   - Tick the AA/DPDP **consent** box, then **Capture consent & score**.
3. The Health Card renders live (usually < 1 s): composite score + tier, the **5 pillar sub-scores**
   (radar), the **SHAP force plot** + top-5 reason codes, the data-source coverage, and the parallel
   **WOE scorecard**.
4. **Show the NTC story:** score a *different* borrower with the **GSTIN left blank** and a fresh
   URN/PAN. Many such firms come back with an **empty Bureau pillar** — watch the dashboard
   **renormalise the pillar weights** to sum to 100% (Bureau 10% redistributes to Cash Flow / GST).
   The PD itself is unchanged — the model handled the missing source natively.
5. Open **Portfolio Heat Map** — every borrower you scored appears, tier-colour-coded. Click a card
   to open the **Drill-down** (score trend, radar, force plot, feature snapshot, alert history).
6. Upload a power bill (`data\raw_payloads\<id>\electricity_bill.txt`) via `POST /bill/upload` in
   `/docs` to see the **async electricity enrichment** (off the origination path).
7. Open **Alert Feed**, sign in as `officer / officer123!`, and click **Run daily monitor**
   (Mode B) to re-score the portfolio and emit tier-crossing / score-drop alerts over WebSocket.

---

## Key API calls (also in Swagger at `/docs`)

```bash
# 1. login
curl -X POST localhost:8000/auth/login -d "username=rm&password=rm123!"

# 2. score (Mode A origination)  — needs the Bearer token from step 1
curl -X POST localhost:8000/score -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"identifiers":{"urn":"UDYAM-MH-03-1234567","pan":"ABCDE1234F","gstin":"27ABCDE1234F1Z5"}}'

# 3. OCEN-compliant assessment (LSP-facing, untrusted boundary)
curl -X POST localhost:8000/ocen/assess -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"borrower":{"urn":"UDYAM-MH-03-1234567","pan":"ABCDE1234F"},"lsp_id":"LSP-001"}'
```

---

## Deployment (Vercel + Render + Neon)

- **Frontend → Vercel:** project root `frontend/`, build `npm run build`, output `dist/`. Set env
  `VITE_API_BASE` to the Render backend URL (e.g. `https://msme-api.onrender.com`).
- **Backend → Render:** root = repo root. Build `pip install ./ml && pip install -r backend/requirements.txt`.
  Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`. Env: `MSME_DATABASE_URL`
  (Neon URL), `MSME_JWT_SECRET` (strong), `MSME_CORS_ORIGINS` (the Vercel domain).
- **Database → Neon:** create a Postgres database; use its `postgresql+psycopg2://...` URL. Tables
  are created automatically on first startup.

## Tests & lint

```bat
cd ml      && ..\ml\.venv\Scripts\python -m pytest        &  :: ML tests (incl. AUC gate)
cd backend && ..\ml\.venv\Scripts\python -m pytest        &  :: API tests (auth/score/OCEN/RBAC)
cd frontend && npm run build                                 :: type-check + build
ml\.venv\Scripts\python -m ruff check ml\msme_ml backend\app :: lint
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/healthz` shows `model_ready: false` | Ensure `backend/model_artifacts/` has `xgb_model.json` + `model_metadata.json` (bundled in the repo). |
| Backend import crash on Windows (exit `0xC0000005`) | Ensure `KMP_DUPLICATE_LIB_OK=TRUE` (the launchers set it). It resolves the duplicate OpenMP-runtime clash between numpy/xgboost/optbinning. |
| `Data-quality gate failed` on `/score` | The AA (bank) source must be present; check the connector diagnostics in the 422 body. |
| Port already in use | Change `--port` in `start-backend.bat` or Vite `--port` in `start-frontend.bat`. |
| MLflow protobuf conflict | Pins are reconciled in `ml/requirements.txt` (ortools 9.8 + protobuf 4.25). |
