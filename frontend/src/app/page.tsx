"use client";

import React, { useState, useEffect } from "react";
import { Activity, CreditCard, ShieldCheck, TrendingUp, DollarSign, Bell, LogOut, Loader2, Moon, Sun, History, X } from "lucide-react";
import { getHealth, login } from "@/lib/api";
import ApplicationForm from "@/components/ApplicationForm";
import ModelAnalysisView from "@/components/views/ModelAnalysisView";
import ReportsView from "@/components/views/ReportsView";
import SettingsView from "@/components/views/SettingsView";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/lib/store";
import RegisterForm from "@/components/RegisterForm";

export default function Dashboard() {
  const { token, username: authUsername, isAuthenticated, login: authLogin, logout, initialize } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showNotification, setShowNotification] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'model' | 'reports' | 'settings'>('dashboard');

  useEffect(() => {
    setMounted(true);
  }, []);
  
  // Login State
  const [authView, setAuthView] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Data State
  const [healthStatus, setHealthStatus] = useState<{status: string, uptime_seconds?: number} | null>(null);

  const [historyToLoad, setHistoryToLoad] = useState<any>(null);

  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated]);

  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      const health = await getHealth();
      setHealthStatus(health);
    } catch (err) {
      console.error("Failed to fetch health:", err);
    }
    try {
      const { getDashboardStats } = await import("@/lib/api");
      const stats = await getDashboardStats();
      setDashboardStats(stats);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const { getApplicationsHistory } = await import("@/lib/api");
      const res = await getApplicationsHistory();
      setHistoryData(res.applications || []);
    } catch (err) {
      console.error("Failed to fetch history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setLoginError("");
    try {
      const res = await login(username, password);
      if (res.access_token) {
        authLogin(res.access_token, res.username, res.role);
        // fetchData is called by the useEffect watching isAuthenticated
      }
    } catch (err: any) {
      setLoginError(err.message || "Login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    logout();
  };

  // Inactivity Auto-Logout (5 minutes)
  useEffect(() => {
    if (!isAuthenticated) return;

    let inactivityTimer: NodeJS.Timeout;

    const resetTimer = () => {
      clearTimeout(inactivityTimer);
      // 5 minutes = 300,000 ms
      inactivityTimer = setTimeout(() => {
        handleLogout();
      }, 5 * 60 * 1000);
    };

    // Events that denote activity
    window.addEventListener("mousemove", resetTimer);
    window.addEventListener("keydown", resetTimer);
    window.addEventListener("click", resetTimer);
    window.addEventListener("scroll", resetTimer, true);

    resetTimer(); // initialize

    return () => {
      clearTimeout(inactivityTimer);
      window.removeEventListener("mousemove", resetTimer);
      window.removeEventListener("keydown", resetTimer);
      window.removeEventListener("click", resetTimer);
      window.removeEventListener("scroll", resetTimer, true);
    };
  }, [isAuthenticated, logout]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-dark-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-dark-800 rounded-2xl p-8 shadow-premium border border-slate-200 dark:border-dark-700">
          <div className="flex items-center justify-center mb-8">
            <div className="w-10 h-10 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-2xl mr-3 shadow-glow">F</div>
            <span className="text-2xl font-heading font-bold text-slate-800 dark:text-white tracking-tight">FinWise<span className="text-brand-500">ML</span></span>
          </div>

          <h1 className="text-center text-lg font-semibold text-slate-700 dark:text-slate-200 mb-6">
            {authView === 'login' ? 'Hesabınıza giriş yapın' : 'Yeni hesap oluşturun'}
          </h1>

          {authView === 'register' ? (
            <RegisterForm
              onAuthenticated={authLogin}
              onSwitchToLogin={() => { setAuthView('login'); setLoginError(""); }}
            />
          ) : (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kullanıcı Adı</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Şifre</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            {loginError && <p className="text-red-500 text-sm">{loginError}</p>}
            <button type="submit" disabled={isLoggingIn} className="w-full py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-medium transition-all shadow-md flex justify-center items-center">
              {isLoggingIn ? <Loader2 className="animate-spin" /> : "Giriş Yap"}
            </button>

            <p className="text-center text-sm text-slate-500 dark:text-slate-400">
              Hesabınız yok mu?{" "}
              <button
                id="switch-to-register"
                type="button"
                onClick={() => { setAuthView('register'); setLoginError(""); }}
                className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
              >
                Hesap Oluştur
              </button>
            </p>
          </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-900 transition-colors duration-300">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 h-16 bg-white/80 dark:bg-dark-800/80 backdrop-blur-md border-b border-slate-200 dark:border-dark-700 flex items-center justify-between px-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-xl shadow-glow">F</div>
          <span className="text-xl font-heading font-bold text-slate-800 dark:text-white tracking-tight">FinWise<span className="text-brand-500">ML</span></span>
          <div className="hidden sm:flex items-center ml-4 gap-1">
            <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-full text-[10px] font-bold uppercase tracking-wider">Live</span>
            <span className="px-2 py-0.5 bg-slate-100 dark:bg-dark-700 text-slate-500 dark:text-slate-400 rounded-full text-[10px] font-medium">v2.6</span>
          </div>
        </div>
        
        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          <button onClick={() => setActiveTab('dashboard')} className={`transition ${activeTab === 'dashboard' ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white'}`}>Dashboard</button>
          <button onClick={() => setActiveTab('model')} className={`transition ${activeTab === 'model' ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white'}`}>Model Analizi</button>
          <button onClick={() => setActiveTab('reports')} className={`transition ${activeTab === 'reports' ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white'}`}>Raporlar</button>
          <button onClick={() => setActiveTab('settings')} className={`transition ${activeTab === 'settings' ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white'}`}>Ayarlar</button>
        </div>
        
        <div className="flex items-center gap-2">
          <button 
            onClick={() => { setShowHistory(true); loadHistory(); }}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-dark-700 rounded-xl transition-colors"
          >
            <History size={18} /> <span className="hidden sm:inline">Başvuru Geçmişi</span>
          </button>
          <button onClick={() => fetchData()} className={`p-2 transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-dark-700 ${isRefreshing ? 'text-brand-500 animate-spin' : 'text-slate-400 hover:text-brand-500'}`} title="Verileri Yenile" aria-label="Verileri yenile">
            <Activity size={18} />
          </button>
          {mounted && (
            <button 
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 text-slate-400 hover:text-brand-500 transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-dark-700"
              title="Tema Değiştir"
              aria-label={theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          )}
          <div className="relative">
            <button onClick={() => setShowNotification(!showNotification)} className="p-2 text-slate-400 hover:text-brand-500 transition-colors relative rounded-lg hover:bg-slate-100 dark:hover:bg-dark-700" title="Bildirimler" aria-label="Bildirimleri göster">
              <Bell size={18} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            {showNotification && (
              <div className="absolute top-full right-0 mt-2 w-72 bg-white dark:bg-dark-800 shadow-xl rounded-lg border border-slate-200 dark:border-dark-700 p-4 z-50">
                <h3 className="font-semibold text-slate-800 dark:text-white mb-2 border-b border-slate-100 dark:border-dark-700 pb-2">Bildirimler</h3>
                <div className="text-sm text-slate-600 dark:text-slate-300 py-4 text-center">Şu anda yeni bildiriminiz bulunmuyor.</div>
                <button onClick={() => setShowNotification(false)} className="mt-2 w-full bg-slate-100 dark:bg-dark-700 text-slate-600 dark:text-slate-300 py-1.5 rounded text-sm hover:bg-slate-200 dark:hover:bg-dark-600 transition-colors">Kapat</button>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 pl-3 border-l border-slate-200 dark:border-dark-700">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{authUsername || "Kullanıcı"}</p>
            </div>
            <button onClick={handleLogout} className="w-9 h-9 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center text-red-600 font-bold border border-red-200 dark:border-red-800 hover:bg-red-200 transition-colors" title="Çıkış Yap" aria-label="Oturumu kapat">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto px-4 sm:px-6 lg:px-10 py-6 space-y-6">
        
        {/* Top Stats Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Toplam Başvuru" value={dashboardStats?.total_applications?.toString() || "—"} trend={dashboardStats?.application_trend || ""} icon={<CreditCard className="text-brand-600" size={20} />} />
          <StatCard title="Onay Oranı" value={dashboardStats?.approval_rate ? `${dashboardStats.approval_rate}%` : "—"} trend={dashboardStats?.approval_trend || ""} icon={<TrendingUp className="text-emerald-500" size={20} />} />
          <StatCard title="Toplam Hacim" value={dashboardStats?.total_volume || "—"} trend={dashboardStats?.volume_trend || ""} icon={<DollarSign className="text-brand-600" size={20} />} />
          <StatCard title="Adillik Skoru" value={dashboardStats?.di_score?.toString() || "—"} trend={dashboardStats?.di_trend || ""} trendType={dashboardStats?.di_score && dashboardStats.di_score < 0.80 ? "warning" : "success"} icon={<ShieldCheck className="text-amber-500" size={20} />} />
        </div>

        {/* API Health Compact Bar */}
        <div className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-dark-800 rounded-xl border border-slate-200 dark:border-dark-700 shadow-sm">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${healthStatus?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></div>
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
            API: {healthStatus ? `${healthStatus.status} • Uptime: ${healthStatus.uptime_seconds}s` : "Bağlanıyor..."}
          </span>
        </div>

        {/* Dynamic Views */}
        {activeTab === 'dashboard' && (
          <ApplicationForm 
            initialData={historyToLoad} 
            onLoaded={() => setHistoryToLoad(null)} 
          />
        )}
        {activeTab === 'model' && <ModelAnalysisView />}
        {activeTab === 'reports' && <ReportsView />}
        {activeTab === 'settings' && <SettingsView />}

      </main>

      {/* History Drawer */}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={() => setShowHistory(false)}></div>
          <div className="relative w-full max-w-lg bg-white dark:bg-dark-800 shadow-2xl border-l border-slate-200 dark:border-dark-700 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-dark-700">
              <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <History size={20} className="text-brand-500" /> Başvuru Geçmişi
              </h3>
              <button onClick={() => setShowHistory(false)} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-dark-700 text-slate-400 hover:text-slate-600 dark:hover:text-white transition">
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-5">
              {historyLoading ? (
                <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin text-brand-500" size={32} /></div>
              ) : historyData.length === 0 ? (
                <div className="py-12 text-center text-slate-500 dark:text-slate-400">Veritabanında başvuru bulunamadı.</div>
              ) : (
                <div className="space-y-3">
                  {historyData.map((app, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => {
                        setHistoryToLoad(app);
                        setActiveTab('dashboard');
                        setShowHistory(false);
                      }}
                      className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-100 dark:border-dark-700 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold ${
                          app.decision === 'Approved' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30' : 'bg-red-100 text-red-600 dark:bg-red-900/30'
                        }`}>
                          {app.decision === 'Approved' ? '✓' : '✕'}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-800 dark:text-white">
                            Başvuru #{app.id || app.application_id}
                            <span className={`text-xs ml-2 px-2 py-0.5 rounded-full ${
                              app.decision === 'Approved' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            }`}>
                              {app.decision === 'Approved' ? 'Onaylandı' : 'Reddedildi'}
                            </span>
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Risk: {app.risk_score?.toFixed(2) || '-'} • {app.model_used || 'XGBoost'}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value, trend, trendType = "success", icon }: { title: string, value: string, trend: string, trendType?: "success"|"warning"|"danger", icon: React.ReactNode }) {
  const trendColors = {
    success: "text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400",
    warning: "text-amber-600 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400",
    danger: "text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <div className="glass-panel rounded-2xl p-5 shadow-sm hover:shadow-premium-hover transition-all duration-300 border border-slate-200 dark:border-dark-700 group hover:-translate-y-1">
      <div className="flex justify-between items-start mb-3">
        <div className="p-2.5 bg-brand-50 dark:bg-brand-900/20 rounded-xl group-hover:scale-110 transition-transform">
          {icon}
        </div>
        {trend && (
          <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${trendColors[trendType]}`}>
            {trend}
          </span>
        )}
      </div>
      <div>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{title}</p>
        <p className="text-2xl font-heading font-bold text-slate-800 dark:text-white mt-1">{value}</p>
      </div>
    </div>
  );
}
