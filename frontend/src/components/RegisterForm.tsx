"use client";

import React, { useMemo, useState } from "react";
import { Loader2, Check, X, KeyRound } from "lucide-react";
import { register, login } from "@/lib/api";

interface RegisterFormProps {
  /** Called after successful signup + automatic login */
  onAuthenticated: (token: string, username: string, role: string) => void;
  onSwitchToLogin: () => void;
}

const inputClass =
  "w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none";
const labelClass = "block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1";

/** Mirrors backend _is_strong_password() in app_v2_secure.py */
function getPasswordRules(password: string) {
  return [
    { label: "En az 10 karakter", ok: password.length >= 10 },
    { label: "Büyük harf (A-Z)", ok: /[A-Z]/.test(password) },
    { label: "Küçük harf (a-z)", ok: /[a-z]/.test(password) },
    { label: "Rakam (0-9)", ok: /\d/.test(password) },
  ];
}

export default function RegisterForm({ onAuthenticated, onSwitchToLogin }: RegisterFormProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const rules = useMemo(() => getPasswordRules(password), [password]);
  const passwordValid = rules.every((r) => r.ok);
  const passwordsMatch = password.length > 0 && password === passwordConfirm;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!passwordValid) {
      setError("Şifre gereksinimlerini karşılamıyor.");
      return;
    }
    if (!passwordsMatch) {
      setError("Şifreler eşleşmiyor.");
      return;
    }

    setIsSubmitting(true);
    try {
      const trimmedUsername = username.trim();
      await register({
        username: trimmedUsername,
        email: email.trim(),
        password,
        invite_code: inviteCode.trim(),
      });
      // Auto-login right after successful registration
      const res = await login(trimmedUsername, password);
      onAuthenticated(res.access_token, res.username, res.role);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kayıt başarısız oldu.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" aria-label="Hesap oluşturma formu">
      <div>
        <label htmlFor="register-username" className={labelClass}>Kullanıcı Adı</label>
        <input
          id="register-username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          minLength={3}
          maxLength={80}
          className={inputClass}
        />
      </div>

      <div>
        <label htmlFor="register-email" className={labelClass}>E-posta</label>
        <input
          id="register-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={120}
          className={inputClass}
        />
      </div>

      <div>
        <label htmlFor="register-password" className={labelClass}>Şifre</label>
        <input
          id="register-password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className={inputClass}
        />
        {password.length > 0 && (
          <ul className="mt-2 grid grid-cols-2 gap-1" aria-live="polite">
            {rules.map((rule) => (
              <li
                key={rule.label}
                className={`flex items-center gap-1.5 text-xs transition-colors ${
                  rule.ok ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"
                }`}
              >
                {rule.ok ? <Check size={12} /> : <X size={12} />}
                {rule.label}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <label htmlFor="register-password-confirm" className={labelClass}>Şifre (Tekrar)</label>
        <input
          id="register-password-confirm"
          type="password"
          autoComplete="new-password"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          required
          className={inputClass}
        />
        {passwordConfirm.length > 0 && !passwordsMatch && (
          <p className="mt-1 text-xs text-red-500">Şifreler eşleşmiyor.</p>
        )}
      </div>

      <div>
        <label htmlFor="register-invite-code" className={labelClass}>Davet Kodu</label>
        <div className="relative">
          <KeyRound size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            id="register-invite-code"
            type="text"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            required
            placeholder="FW-XXXXXXXXXX"
            className={`${inputClass} pl-9 font-mono tracking-wide`}
          />
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Davet kodunu sistem yöneticinizden alabilirsiniz.
        </p>
      </div>

      {error && <p className="text-red-500 text-sm" role="alert">{error}</p>}

      <button
        id="register-submit"
        type="submit"
        disabled={isSubmitting}
        className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white rounded-xl font-medium transition-all shadow-md flex justify-center items-center"
      >
        {isSubmitting ? <Loader2 className="animate-spin" /> : "Hesap Oluştur"}
      </button>

      <p className="text-center text-sm text-slate-500 dark:text-slate-400">
        Zaten hesabınız var mı?{" "}
        <button
          id="switch-to-login"
          type="button"
          onClick={onSwitchToLogin}
          className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
        >
          Giriş Yap
        </button>
      </p>
    </form>
  );
}
