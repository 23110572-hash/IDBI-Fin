export interface TierStyle {
  key: string;
  label: string;
  color: string;
  bg: string;
  text: string;
  ring: string;
}

const STYLES: Record<string, TierStyle> = {
  excellent: { key: "excellent", label: "Excellent", color: "#15803d", bg: "bg-green-100", text: "text-green-800", ring: "ring-green-500" },
  good: { key: "good", label: "Good", color: "#65a30d", bg: "bg-lime-100", text: "text-lime-800", ring: "ring-lime-500" },
  fair: { key: "fair", label: "Fair", color: "#ca8a04", bg: "bg-yellow-100", text: "text-yellow-800", ring: "ring-yellow-500" },
  watch: { key: "watch", label: "Watch", color: "#ea580c", bg: "bg-orange-100", text: "text-orange-800", ring: "ring-orange-500" },
  risk: { key: "risk", label: "Risk", color: "#dc2626", bg: "bg-red-100", text: "text-red-800", ring: "ring-red-500" },
  high_risk: { key: "high_risk", label: "High Risk", color: "#991b1b", bg: "bg-red-200", text: "text-red-900", ring: "ring-red-700" },
};

export function tierStyle(tier: string): TierStyle {
  return STYLES[tier] ?? STYLES.fair;
}

export function scoreColor(score: number): string {
  if (score >= 90) return STYLES.excellent.color;
  if (score >= 75) return STYLES.good.color;
  if (score >= 60) return STYLES.fair.color;
  if (score >= 40) return STYLES.watch.color;
  if (score >= 20) return STYLES.risk.color;
  return STYLES.high_risk.color;
}

export const PILLAR_ORDER = [
  "cash_flow_stability",
  "gst_compliance_revenue",
  "business_stability",
  "bureau_credit_history",
  "macroeconomic_context",
];

export const SOURCE_LABELS: Record<string, string> = {
  aa: "Account Aggregator",
  gst: "GST Network",
  bureau: "Credit Bureau",
  epfo: "EPFO",
  upi: "UPI (NPCI)",
  udyam: "Udyam",
  macro: "Macro (RBI/PMI)",
  electricity: "Electricity",
};
