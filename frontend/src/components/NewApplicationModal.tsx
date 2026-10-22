"use client";

import React, { useState } from "react";
import { Loader2, X, AlertCircle, CheckCircle2 } from "lucide-react";
import { evaluateCredit } from "@/lib/api";

export default function NewApplicationModal({ isOpen, onClose, onSuccess }: { isOpen: boolean, onClose: () => void, onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");

  const [formData, setFormData] = useState({
    person_age: "30",
    person_income: "60000",
    person_emp_length: "5",
    loan_amnt: "10000",
    loan_int_rate: "11.5",
    loan_percent_income: "0.16",
    cb_person_cred_hist_length: "4",
    person_home_ownership: "RENT",
    loan_intent: "PERSONAL",
    loan_grade: "B",
    cb_person_default_on_file: "N",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      // Typecasting everything properly is handled in the backend, but we send as strings/numbers
      const res = await evaluateCredit(formData);
      setResult(res);
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Değerlendirme sırasında bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-dark-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col border border-slate-200 dark:border-dark-700">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-dark-700">
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">Yeni Başvuru Değerlendir</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-dark-700 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {result ? (
            <div className="flex flex-col items-center justify-center py-8 text-center animate-in fade-in zoom-in duration-300">
              {result.decision === "Approved" ? (
                <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 rounded-full flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(16,185,129,0.3)]">
                  <CheckCircle2 size={40} />
                </div>
              ) : (
                <div className="w-20 h-20 bg-red-100 dark:bg-red-900/30 text-red-500 rounded-full flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(239,68,68,0.3)]">
                  <AlertCircle size={40} />
                </div>
              )}
              
              <h3 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">
                {result.decision === "Approved" ? "Başvuru Onaylandı" : "Başvuru Reddedildi"}
              </h3>
              
              <div className="bg-slate-50 dark:bg-dark-900 rounded-xl p-6 mt-6 max-w-sm w-full border border-slate-100 dark:border-dark-700">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-slate-500 dark:text-slate-400">Risk Skoru:</span>
                  <span className="font-bold text-lg text-slate-800 dark:text-white">{result.risk_score?.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center mb-3">
                  <span className="text-slate-500 dark:text-slate-400">Onay Olasılığı:</span>
                  <span className="font-bold text-lg text-slate-800 dark:text-white">{(result.onay_olasiligi * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 dark:text-slate-400">Uygulanan Eşik:</span>
                  <span className="font-bold text-slate-800 dark:text-white">{result.applied_threshold}</span>
                </div>
              </div>

              <div className="mt-8 flex gap-4">
                <button onClick={() => setResult(null)} className="px-6 py-2.5 border border-slate-200 dark:border-dark-700 text-slate-600 dark:text-slate-300 rounded-xl font-medium hover:bg-slate-50 dark:hover:bg-dark-700 transition-colors">
                  Yeni Başvuru
                </button>
                <button onClick={onClose} className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-medium transition-colors shadow-md">
                  Kapat
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yaş (person_age)</label>
                  <input type="number" name="person_age" value={formData.person_age} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Gelir (person_income)</label>
                  <input type="number" name="person_income" value={formData.person_income} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Çalışma Süresi (Yıl)</label>
                  <input type="number" name="person_emp_length" value={formData.person_emp_length} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Geçmişi (Yıl)</label>
                  <input type="number" name="cb_person_cred_hist_length" value={formData.cb_person_cred_hist_length} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Tutarı (loan_amnt)</label>
                  <input type="number" name="loan_amnt" value={formData.loan_amnt} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Faiz Oranı (loan_int_rate)</label>
                  <input type="number" step="0.1" name="loan_int_rate" value={formData.loan_int_rate} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi / Gelir Oranı</label>
                  <input type="number" step="0.01" name="loan_percent_income" value={formData.loan_percent_income} onChange={handleChange} required className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ev Sahipliği</label>
                  <select name="person_home_ownership" value={formData.person_home_ownership} onChange={handleChange} className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none">
                    <option value="RENT">Kira (RENT)</option>
                    <option value="OWN">Ev Sahibi (OWN)</option>
                    <option value="MORTGAGE">İpotekli (MORTGAGE)</option>
                    <option value="OTHER">Diğer (OTHER)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Amacı</label>
                  <select name="loan_intent" value={formData.loan_intent} onChange={handleChange} className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none">
                    <option value="PERSONAL">Kişisel (PERSONAL)</option>
                    <option value="EDUCATION">Eğitim (EDUCATION)</option>
                    <option value="MEDICAL">Sağlık (MEDICAL)</option>
                    <option value="VENTURE">Girişim (VENTURE)</option>
                    <option value="HOMEIMPROVEMENT">Ev Geliştirme</option>
                    <option value="DEBTCONSOLIDATION">Borç Kapatma</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Notu</label>
                  <select name="loan_grade" value={formData.loan_grade} onChange={handleChange} className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none">
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                    <option value="E">E</option>
                    <option value="F">F</option>
                    <option value="G">G</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Geçmiş Temerrüt</label>
                  <select name="cb_person_default_on_file" value={formData.cb_person_default_on_file} onChange={handleChange} className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none">
                    <option value="N">Hayır (N)</option>
                    <option value="Y">Evet (Y)</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 rounded-xl flex items-center gap-3">
                  <AlertCircle size={20} />
                  <p>{error}</p>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-6 border-t border-slate-200 dark:border-dark-700">
                <button type="button" onClick={onClose} className="px-6 py-2.5 text-slate-600 dark:text-slate-400 font-medium hover:bg-slate-100 dark:hover:bg-dark-700 rounded-xl transition-colors">
                  İptal
                </button>
                <button type="submit" disabled={loading} className="px-8 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-medium transition-colors shadow-md flex items-center justify-center">
                  {loading ? <Loader2 className="animate-spin mr-2" size={20} /> : null}
                  Değerlendir
                </button>
              </div>

            </form>
          )}
        </div>
      </div>
    </div>
  );
}
