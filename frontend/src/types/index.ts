export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  invite_code?: string;
}

export interface RegisterResponse {
  message: string;
  username: string;
}

export interface DashboardStats {
  total_applications: number;
  approval_rate: number | string;
  total_volume: string;
  di_score: number;
  application_trend?: string;
  approval_trend?: string;
  volume_trend?: string;
  di_trend?: string;
}

export interface ShapFeature {
  feature: string;
  contribution?: number;
  value?: number;
  impact?: number;
  direction?: string;
}

export interface CreditEvaluationRequest {
  person_age: string | number;
  person_income: string | number;
  person_emp_length: string | number;
  loan_amnt: string | number;
  loan_int_rate: string | number;
  loan_percent_income: string | number;
  cb_person_cred_hist_length: string | number;
  person_home_ownership: string;
  loan_intent: string;
  loan_grade: string;
  cb_person_default_on_file: string;
}

export interface FraudAnalysis {
  is_fraud: boolean;
  score: number;
  reasons: string[];
}

export interface CreditEvaluationResponse {
  tahmin?: string;
  onay_olasiligi?: number;
  red_olasiligi?: number;
  shap_top_features?: ShapFeature[];
  fraud_risk?: number;
  decision?: string;
  fraud_analysis?: FraudAnalysis;
}

export interface Application {
  id?: number;
  application_id?: number;
  applicant_name?: string;
  decision: string;
  risk_score?: number;
  model_used?: string;
}

export interface HistoryResponse {
  applications: Application[];
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
  last_login: string | null;
  evaluated_count: number;
}

export interface BankOffer {
  bank_id: string;
  bank_name: string;
  product_name: string;
  color: string;
  badge: string;
  badge_type: string;
  sponsored: boolean;
  features: string[];
  apply_url: string;
  loan_amount: number;
  term_months: number;
  monthly_interest_rate: number;
  monthly_installment: number;
  total_repayment: number;
  total_interest_and_tax: number;
  processing_fee: number;
  annual_cost_rate: number;
  currency: string;
  is_preapproved: boolean;
}

export interface BankOffersResponse {
  status: string;
  loan_amount: number;
  term_months: number;
  risk_score: number;
  decision: string;
  is_approved: boolean;
  currency: string;
  offers_count: number;
  offers: BankOffer[];
  disclaimer: string;
}

export interface FeatureDriftMetric {
  type: "numeric" | "categorical";
  psi: number;
  ks_statistic?: number;
  ks_pvalue?: number;
  drift_detected: boolean;
  status: "NORMAL" | "WARNING" | "CRITICAL";
  baseline_mean?: number;
  current_mean?: number;
  top_baseline_category?: string;
  top_current_category?: string;
}

export interface DriftAnalysisResponse {
  overall_status: "STABLE" | "MODERATE_DRIFT" | "CRITICAL_DRIFT";
  overall_psi: number;
  max_feature_psi: number;
  severity: "success" | "warning" | "danger";
  drifted_features_count: number;
  total_evaluated_features: number;
  total_live_applications_in_db: number;
  evaluation_window_size: number;
  sample_warning?: boolean;
  sample_warning_message?: string;
  summary_message: string;
  recommendations: string[];
  features: Record<string, FeatureDriftMetric>;
  threshold_benchmarks: {
    stable: string;
    moderate: string;
    critical: string;
  };
}
