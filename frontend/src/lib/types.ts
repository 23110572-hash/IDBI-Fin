export interface Pillar {
  pillar: string;
  label: string;
  primary_source: string;
  sub_score: number;
  display_weight: number;
  base_weight: number;
  available: boolean;
}

export interface ReasonCode {
  feature: string;
  label: string;
  category: string;
  shap: number;
  direction: string;
  impact: "positive" | "negative";
  value: number | null;
  actionable: boolean;
  unit: string;
}

export interface HealthCard {
  pd: number;
  composite_score: number;
  tier: string;
  tier_label: string;
  action: string;
  segment_label: string;
  confidence: number;
  pillars: Pillar[];
  reason_codes: ReasonCode[];
  model_version: string;
  available_sources: Record<string, boolean>;
}

export interface ScoreResponse {
  score_id: string;
  urn: string;
  business_name: string | null;
  mode: string;
  latency_ms: number;
  health_card: HealthCard;
  scorecard: ScorecardSnapshot | null;
  data_quality: DataQuality | null;
  created_at: string;
}

export interface ScorecardSnapshot {
  engine: string;
  note: string;
  features: string[];
  points_table: Record<string, unknown>[];
}

export interface DataQuality {
  feature_coverage: number;
  features_present: number;
  features_total: number;
  passed: boolean;
  critical_source_aa_present: boolean;
  connector_diagnostics?: { source: string; status: string; latency_ms: number }[];
}

export interface PortfolioBorrower {
  urn: string;
  business_name: string | null;
  score_id: string;
  composite_score: number;
  tier: string;
  tier_label: string;
  pd: number;
  confidence: number;
  segment: string | null;
  sector: string | null;
  sub_scores: Record<string, number>;
  available_sources: Record<string, boolean>;
  created_at: string;
}

export interface HistoryEntry {
  score_id: string;
  composite_score: number;
  tier: string;
  tier_label: string;
  pd: number;
  mode: string;
  model_version: string;
  sub_scores: Record<string, number>;
  reason_codes: ReasonCode[];
  pillars: Pillar[];
  available_sources: Record<string, boolean>;
  created_at: string;
}

export interface Alert {
  alert_id: string;
  urn: string;
  type: string;
  severity: string;
  message: string;
  suggested_action: string;
  created_at: string;
}
