"use client";

import React, { useState, useEffect, useMemo, useSyncExternalStore } from "react";
import { 
  Settings, 
  User as UserIcon, 
  KeyRound, 
  ShieldCheck, 
  Mail, 
  Calendar, 
  Activity, 
  Check, 
  X, 
  Loader2, 
  Save, 
  LogOut, 
  Clock, 
  Server, 
  Moon, 
  Sun 
} from "lucide-react";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/lib/store";
import { getUserProfile, changePassword, updateProfile } from "@/lib/api";
import { UserProfile } from "@/types";

function getPasswordRules(password: string) {
  return [
    { label: "En az 10 karakter", ok: password.length >= 10 },
    { label: "Büyük harf (A-Z)", ok: /[A-Z]/.test(password) },
    { label: "Küçük harf (a-z)", ok: /[a-z]/.test(password) },
    { label: "Rakam (0-9)", ok: /\d/.test(password) },
  ];
}

const emptySubscribe = () => () => {};

export default function SettingsView() {
  const { theme, setTheme } = useTheme();
  const { username: authUsername, role: authRole, logout } = useAuthStore();
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);

  // User profile state
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState("");

  // Edit email state
  const [emailInput, setEmailInput] = useState("");
  const [isUpdatingEmail, setIsUpdatingEmail] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState("");
  const [emailError, setEmailError] = useState("");

  // Change password state
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPass, setIsChangingPass] = useState(false);
  const [passSuccess, setPassSuccess] = useState("");
  const [passError, setPassError] = useState("");

  const rules = useMemo(() => getPasswordRules(newPassword), [newPassword]);
  const newPasswordValid = rules.every((r) => r.ok);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      try {
        const data = await getUserProfile();
        if (!ignore) {
          setProfile(data);
          setEmailInput(data.email || "");
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Profil bilgileri yüklenemedi";
          setProfileError(msg);
        }
      } finally {
        if (!ignore) {
          setProfileLoading(false);
        }
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, []);

  const handleUpdateEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError("");
    setEmailSuccess("");
    if (!emailInput.trim()) {
      setEmailError("E-posta adresi boş bırakılamaz.");
      return;
    }

    setIsUpdatingEmail(true);
    try {
      const res = await updateProfile(emailInput.trim());
      setEmailSuccess(res.message || "E-posta başarıyla güncellendi.");
      if (profile) {
        setProfile({ ...profile, email: res.email });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "E-posta güncellenemedi.";
      setEmailError(msg);
    } finally {
      setIsUpdatingEmail(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPassError("");
    setPassSuccess("");

    if (!newPasswordValid) {
      setPassError("Yeni şifre güvenlik kurallarını sağlamıyor.");
      return;
    }
    if (!passwordsMatch) {
      setPassError("Yeni şifreler eşleşmiyor.");
      return;
    }

    setIsChangingPass(true);
    try {
      const res = await changePassword(oldPassword, newPassword);
      setPassSuccess(res.message || "Şifreniz başarıyla güncellendi.");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Şifre güncellenemedi.";
      setPassError(msg);
    } finally {
      setIsChangingPass(false);
    }
  };

  // Get user role in Turkish
  const getRoleBadge = (roleName?: string) => {
    switch (roleName?.toLowerCase()) {
      case "admin":
        return { label: "Sistem Yöneticisi (Admin)", color: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300" };
      case "manager":
        return { label: "Kredi Yöneticisi (Manager)", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" };
      default:
        return { label: "Risk Analisti (Analyst)", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" };
    }
  };

  const currentRole = getRoleBadge(profile?.role || authRole || "analyst");

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Üst Başlık Kartı */}
      <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <Settings className="text-brand-500" /> Kullanıcı & Sistem Ayarları
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Profil bilgilerinizi yönetin, şifrenizi güncelleyin ve sistem tercihlerini özelleştirin.
          </p>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 text-sm font-medium rounded-xl transition border border-red-200 dark:border-red-800/40"
        >
          <LogOut size={16} /> Güvenli Çıkış
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* SOL KOLON: Profil Kartı & Bilgileri */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
            <div className="flex flex-col items-center text-center pb-6 border-b border-slate-100 dark:border-dark-700">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center text-white text-3xl font-black shadow-glow mb-4 uppercase">
                {(profile?.username || authUsername || "K")[0]}
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white capitalize">
                {profile?.username || authUsername || "Kullanıcı"}
              </h3>
              <span className={`mt-2 px-3 py-1 rounded-full text-xs font-bold ${currentRole.color}`}>
                {currentRole.label}
              </span>
            </div>

            {profileError && (
              <div className="mt-3 p-2.5 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 text-xs rounded-xl text-center">
                {profileError}
              </div>
            )}

            {profileLoading ? (
              <div className="py-8 flex justify-center">
                <Loader2 className="animate-spin text-brand-500" />
              </div>
            ) : (
              <div className="pt-5 space-y-4 text-sm">
                <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                  <span className="flex items-center gap-2 text-slate-400">
                    <UserIcon size={16} /> Kullanıcı Adı
                  </span>
                  <span className="font-semibold text-slate-800 dark:text-white">{profile?.username}</span>
                </div>

                <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                  <span className="flex items-center gap-2 text-slate-400">
                    <Activity size={16} /> İncelenen Başvuru
                  </span>
                  <span className="font-semibold text-brand-600 dark:text-brand-400">
                    {profile?.evaluated_count || 0} adet
                  </span>
                </div>

                <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                  <span className="flex items-center gap-2 text-slate-400">
                    <Calendar size={16} /> Üyelik Tarihi
                  </span>
                  <span className="text-xs font-medium">
                    {profile?.created_at ? new Date(profile.created_at).toLocaleDateString('tr-TR') : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
                  <span className="flex items-center gap-2 text-slate-400">
                    <Clock size={16} /> Son Giriş
                  </span>
                  <span className="text-xs font-medium">
                    {profile?.last_login ? new Date(profile.last_login).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }) : "Az önce"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* E-posta Güncelleme Kutusu */}
          <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
            <h4 className="font-bold text-slate-800 dark:text-white mb-3 flex items-center gap-2 text-base">
              <Mail size={18} className="text-brand-500" /> E-posta Adresi
            </h4>
            <form onSubmit={handleUpdateEmail} className="space-y-3">
              <input
                type="email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                required
                className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-500"
              />
              {emailSuccess && <p className="text-emerald-500 text-xs font-medium">{emailSuccess}</p>}
              {emailError && <p className="text-red-500 text-xs font-medium">{emailError}</p>}
              <button
                type="submit"
                disabled={isUpdatingEmail}
                className="w-full py-2 bg-slate-100 hover:bg-slate-200 dark:bg-dark-700 dark:hover:bg-dark-600 text-slate-800 dark:text-white text-xs font-bold rounded-xl transition flex justify-center items-center gap-1.5"
              >
                {isUpdatingEmail ? <Loader2 size={14} className="animate-spin" /> : <><Save size={14} /> E-postayı Güncelle</>}
              </button>
            </form>
          </div>
        </div>

        {/* SAĞ KOLON: Şifre Değiştirme ve Sistem Ayarları */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Şifre Değiştirme Kartı */}
          <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
            <div className="border-b border-slate-100 dark:border-dark-700 pb-4 mb-5">
              <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <KeyRound className="text-amber-500" size={20} /> Şifre Güvenliği & Değiştirme
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Hesabınızın güvenliği için güçlü ve tahmin edilmesi zor bir şifre belirleyin.
              </p>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Mevcut Şifre
                  </label>
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    required
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Yeni Şifre
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>

              {newPassword.length > 0 && (
                <div className="p-3 bg-slate-50 dark:bg-dark-900 rounded-xl border border-slate-100 dark:border-dark-700">
                  <p className="text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5">Şifre Gereksinimleri:</p>
                  <ul className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    {rules.map((rule) => (
                      <li
                        key={rule.label}
                        className={`flex items-center gap-1 font-medium transition-colors ${
                          rule.ok ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"
                        }`}
                      >
                        {rule.ok ? <Check size={12} /> : <X size={12} />} {rule.label}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Yeni Şifre (Tekrar)
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-500"
                />
                {confirmPassword.length > 0 && !passwordsMatch && (
                  <p className="mt-1 text-xs text-red-500">Şifreler eşleşmiyor.</p>
                )}
              </div>

              {passSuccess && <p className="text-emerald-600 dark:text-emerald-400 text-xs font-semibold p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">{passSuccess}</p>}
              {passError && <p className="text-red-500 text-xs font-semibold p-2 bg-red-50 dark:bg-red-950/30 rounded-lg">{passError}</p>}

              <button
                type="submit"
                disabled={isChangingPass}
                className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-bold rounded-xl transition shadow-md flex items-center justify-center gap-2"
              >
                {isChangingPass ? <Loader2 size={16} className="animate-spin" /> : "Şifreyi Değiştir"}
              </button>
            </form>
          </div>

          {/* Sistem & Görünüm Tercihleri */}
          <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm space-y-4">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white border-b border-slate-100 dark:border-dark-700 pb-3">
              Sistem & Güvenlik Tercihleri
            </h3>

            {/* Tema Tercihi */}
            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-dark-900 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-white dark:bg-dark-800 rounded-xl text-brand-500 shadow-sm">
                  {mounted && theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
                </div>
                <div>
                  <p className="font-semibold text-slate-800 dark:text-white text-sm">Arayüz Teması</p>
                  <p className="text-xs text-slate-500">Koyu veya Açık çalışma modunu seçin.</p>
                </div>
              </div>
              {mounted && (
                <div className="flex items-center bg-slate-200 dark:bg-dark-800 p-1 rounded-xl">
                  <button
                    onClick={() => setTheme('light')}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition ${theme === 'light' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
                  >
                    Açık
                  </button>
                  <button
                    onClick={() => setTheme('dark')}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition ${theme === 'dark' ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-500'}`}
                  >
                    Koyu
                  </button>
                </div>
              )}
            </div>

            {/* Oturum Süresi & Güvenlik */}
            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-dark-900 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-white dark:bg-dark-800 rounded-xl text-emerald-500 shadow-sm">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <p className="font-semibold text-slate-800 dark:text-white text-sm">Oturum Koruması (Auto-Logout)</p>
                  <p className="text-xs text-slate-500">5 dakika hareketsizlik halinde oturum otomatik sonlandırılır.</p>
                </div>
              </div>
              <span className="px-3 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-xs font-bold rounded-full">
                Aktif
              </span>
            </div>

            {/* API Backend Durumu */}
            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-dark-900 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-white dark:bg-dark-800 rounded-xl text-blue-500 shadow-sm">
                  <Server size={20} />
                </div>
                <div>
                  <p className="font-semibold text-slate-800 dark:text-white text-sm">Model API Sunucusu</p>
                  <p className="text-xs text-slate-500">Port 5001 • Flask Waitress WSGI • v2.6</p>
                </div>
              </div>
              <span className="px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-mono text-xs rounded-lg font-bold">
                Online
              </span>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
