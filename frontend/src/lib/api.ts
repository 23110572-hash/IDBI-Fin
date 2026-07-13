import axios from "axios";
import { useAuth } from "./store";
import type {
  Alert,
  HistoryEntry,
  PortfolioBorrower,
  ScoreResponse,
} from "./types";

// All calls go directly to the production backend by default.
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || "https://idbi-fin.onrender.com" });

api.interceptors.request.use((config) => {
  const token = useAuth.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) useAuth.getState().logout();
    return Promise.reject(err);
  }
);

export interface Identifiers {
  urn: string;
  pan: string;
  gstin?: string | null;
  business_name?: string | null;
}

export async function login(username: string, password: string) {
  const form = new URLSearchParams({ username, password });
  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data as { access_token: string; role: string; expires_in: number };
}

export async function register(username: string, password: string, role: string) {
  const { data } = await api.post("/auth/register", { username, password, role });
  return data as { access_token: string; role: string; expires_in: number };
}

export async function createConsent(identifiers: Identifiers) {
  const { data } = await api.post("/consent", { identifiers });
  return data as { consent_id: string; consent_handle: string; status: string };
}

export async function scoreBorrower(identifiers: Identifiers, consentId?: string) {
  const { data } = await api.post("/score", {
    identifiers,
    consent_id: consentId,
    include_scorecard: true,
  });
  return data as ScoreResponse;
}

export async function uploadElectricityBill(identifiers: Identifiers, file: File) {
  const fd = new FormData();
  fd.append("urn", identifiers.urn);
  fd.append("pan", identifiers.pan);
  if (identifiers.gstin) fd.append("gstin", identifiers.gstin);
  fd.append("file", file);
  const { data } = await api.post("/bill/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data as {
    message: string;
    ocr: {
      engine: string;
      units_consumed_kwh: number | null;
      sanctioned_load_kw: number | null;
      bill_amount: number | null;
      extracted_ok: boolean;
    };
    enrichment: {
      score_id?: string;
      composite_score?: number;
      health_card?: import("./types").HealthCard;
    } | null;
  };
}

export async function fetchPortfolio() {
  const { data } = await api.get("/portfolio");
  return data.borrowers as PortfolioBorrower[];
}

export async function fetchBorrower(urn: string) {
  const { data } = await api.get(`/borrower/${urn}`);
  return data as { urn: string; history: HistoryEntry[]; latest: HistoryEntry };
}

export async function fetchAlerts() {
  const { data } = await api.get("/alerts");
  return data.alerts as Alert[];
}

export async function runMonitor(trigger = "daily_delta") {
  const { data } = await api.post(`/monitor/run?trigger=${trigger}`);
  return data as { trigger: string; borrowers_scored: number; alerts_created: number };
}

export async function healthz() {
  const { data } = await api.get("/healthz");
  return data;
}
