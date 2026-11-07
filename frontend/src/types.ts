export type MetricSet = {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  hallucination_rate: number;
  overall_score: number | null;
};

export type Finding = {
  code: string;
  category: string;
  severity: string;
  message: string;
  evidence: Record<string, string | number | null>;
  human_review_required: boolean;
};

export type RecordFinding = {
  record_number: number;
  prediction: string;
  reference: string | null;
  verified: boolean | null;
  explanation: string;
  supported: boolean;
  unsupported_claim: boolean;
  human_review_required: boolean;
};

export type EvaluationResult = {
  id: string;
  filename: string;
  created_at: string;
  columns: Array<{
    name: string;
    inferred_type: string;
    missing_count: number;
    unique_count: number;
    identifier_redacted: boolean;
  }>;
  preview: Array<Record<string, string | number | null>>;
  validation: {
    record_count: number;
    column_count: number;
    missing_value_count: number;
    duplicate_count: number;
    issue_count: number;
    quality_summary: {
      data_quality_issue_count: number;
      clinical_review_count: number;
      unusual_value_count: number;
    };
    issues: Finding[];
  };
  evaluation: {
    metrics: MetricSet;
    unsupported_count: number;
    evaluated_record_count: number;
    has_reference_answers: boolean;
    column_mapping: {
      ai_label: string | null;
      reference_answer: string | null;
    };
    verification_summary: {
      verified: number;
      not_verified: number;
      unscored: number;
      scored: number;
    };
    comparison: Array<{ reference: string; prediction: string; count: number }>;
    record_findings: RecordFinding[];
    issues: Finding[];
    methodology: string;
  };
  privacy: {
    raw_dataset_saved: boolean;
    identifiers_redacted_in_preview: boolean;
    stored_fields: string;
  };
};

export type DashboardData = {
  summary: {
    evaluations: number;
    records: number;
    issues: number;
    missing: number;
    unsupported: number;
    average_score: number | null;
  };
  recent_evaluations: Array<{
    id: string;
    filename: string;
    created_at: string;
    record_count: number;
    issue_count: number;
    missing_value_count: number;
    unsupported_count: number;
    score: number | null;
    metrics: MetricSet;
  }>;
  trend: Array<{ date: string; score: number | null; records: number }>;
};
