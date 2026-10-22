/**
 * FinWise ML Platform — Production API Client
 * 
 * Requires NEXT_PUBLIC_API_URL environment variable to be set.
 * Handles JWT authentication, 401 auto-logout, and structured error responses.
 */
import { LoginResponse, RegisterRequest, RegisterResponse, DashboardStats, HistoryResponse, CreditEvaluationRequest, CreditEvaluationResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  console.warn(
    "[FinWise API] NEXT_PUBLIC_API_URL is not set. API calls will fail. " +
    "Set this in your .env.local file, e.g.: NEXT_PUBLIC_API_URL=http://localhost:5000"
  );
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Helper to fetch data from the Flask API.
 * Automatically attaches JWT token and handles 401 (unauthorized) responses.
 */
export async function fetchApi<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  if (!API_URL) {
    throw new ApiError("API URL is not configured. Set NEXT_PUBLIC_API_URL.", 0);
  }

  const url = `${API_URL}${endpoint}`;
  
  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Attach JWT token if available
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      defaultHeaders["Authorization"] = `Bearer ${token}`;
    }
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });
  } catch (error) {
    throw new ApiError("Ağ hatası: Sunucuya bağlanılamadı.", 503);
  }

  // Handle 401 Unauthorized — token expired or invalid
  if (response.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
    // Removed window.location.reload() to let auth layer handle it
    throw new ApiError("Oturum süresi doldu. Lütfen tekrar giriş yapın.", 401);
  }

  if (!response.ok) {
    let errorMsg = "API Error";
    try {
      const errData = await response.json();
      errorMsg = errData.error || errData.message || errorMsg;
    } catch {
      // Response is not JSON
    }
    throw new ApiError(errorMsg, response.status);
  }

  return response.json();
}

/**
 * Check Backend Health
 */
export async function getHealth(): Promise<{ status: string; uptime_seconds: number }> {
  return fetchApi<{ status: string; uptime_seconds: number }>("/health");
}

/**
 * Get Applications History
 */
export async function getApplicationsHistory(): Promise<HistoryResponse> {
  return fetchApi<HistoryResponse>("/api/v2/applications/history");
}

/**
 * Evaluate Credit Risk (Example payload)
 */
export async function evaluateCredit(data: any) {
  return fetchApi('/degerlendir', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchCustomerData(tckn: string) {
  return fetchApi(`/customer/${tckn}`, {
    method: 'GET',
  });
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchApi<DashboardStats>("/api/dashboard-stats");
}

export async function getFairnessReport(): Promise<any> {
  return fetchApi<any>("/fairness/daily");
}

/**
 * Login function
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  return fetchApi<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

/** Backend /auth/register error messages -> Turkish UI labels */
const REGISTER_ERROR_TR: Record<string, string> = {
  "Public registration is disabled": "Yeni kayıtlar şu anda kapalı.",
  "username and password required": "Kullanıcı adı ve şifre zorunludur.",
  "valid email is required": "Geçerli bir e-posta adresi girin.",
  "password must be at least 10 chars and include upper/lowercase letters and digits":
    "Şifre en az 10 karakter olmalı; büyük harf, küçük harf ve rakam içermelidir.",
  "valid invite code is required": "Davet kodu geçersiz.",
  "email domain is not allowed": "Bu e-posta alan adıyla kayıt yapılamıyor.",
  "username already exists": "Bu kullanıcı adı zaten alınmış.",
  "email already exists": "Bu e-posta adresi zaten kayıtlı.",
};

/**
 * Register a new user (self-signup always gets the 'analyst' role on the backend)
 */
export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  try {
    return await fetchApi<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 429) {
        throw new ApiError("Çok fazla kayıt denemesi. Lütfen daha sonra tekrar deneyin.", 429);
      }
      throw new ApiError(REGISTER_ERROR_TR[err.message] ?? err.message, err.status);
    }
    throw err;
  }
}

/**
 * Aktif oturumdaki kullanıcının profil bilgilerini getirir.
 */
export async function getUserProfile() {
  return fetchApi<import("@/types").UserProfile>("/auth/me");
}

/**
 * Kullanıcı şifresini günceller.
 */
export async function changePassword(old_password: string, new_password: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password, new_password }),
  });
}

/**
 * Kullanıcı profil bilgilerini (e-posta vb.) günceller.
 */
export async function updateProfile(email: string): Promise<{ message: string; email: string }> {
  return fetchApi<{ message: string; email: string }>("/auth/update-profile", {
    method: "PUT",
    body: JSON.stringify({ email }),
  });
}

/**
 * Gerçek Türkiye banka tekliflerini hesaplar ve getirir.
 */
export async function getBankOffers(payload: {
  amount?: number | string;
  term_months?: number;
  risk_score?: number;
  decision?: string;
}) {
  return fetchApi<import("@/types").BankOffersResponse>("/api/v2/bank-offers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Canlı popülasyon veri kayması ve PSI (Population Stability Index) analizini getirir.
 */
export async function getModelDrift(windowSize: number = 500) {
  return fetchApi<import("@/types").DriftAnalysisResponse>(`/api/v2/monitoring/drift?window=${windowSize}`);
}

/**
 * Popülasyon kayması hesaplamasını canlı veritabanı kayıtları üzerinden yeniden tetikler.
 */
export async function recalculateModelDrift() {
  return fetchApi<{ message: string; data: import("@/types").DriftAnalysisResponse }>("/api/v2/monitoring/drift/recalculate", {
    method: "POST",
  });
}


