"use client";

import React, { useState, useEffect } from "react";
import { Loader2, AlertCircle, Sparkles, User, BrainCircuit, Info, Eraser, Wand2 } from "lucide-react";
import { evaluateCredit, fetchCustomerData } from "@/lib/api";
import { useTheme } from "next-themes";
import ResultPanel from "./ResultPanel";
import AiChatWidget from "./AiChatWidget";
import CustomSelect from "./CustomSelect";

export default function ApplicationForm({ initialData, onLoaded }: { initialData?: any; onLoaded?: () => void }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");
  const [activeTool, setActiveTool] = useState<'none' | 'shap' | 'fraud' | 'simulator' | 'quote'>('none');
  
  // Profile Guide Modal State
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [currentProfile, setCurrentProfile] = useState<string>("Yok");

  // SHAP State
  const [shapData, setShapData] = useState<{feature: string, value: number}[]>([]);
  const [fraudRisk, setFraudRisk] = useState<number | null>(null);

  // TCKN Search State
  const [tckn, setTckn] = useState("");
  const [isSearchingTckn, setIsSearchingTckn] = useState(false);
  const [tcknError, setTcknError] = useState("");

  const emptyForm = {
    person_age: "",
    person_income: "",
    person_emp_length: "",
    loan_amnt: "",
    loan_int_rate: "",
    loan_percent_income: "",
    cb_person_cred_hist_length: "",
    person_home_ownership: "",
    loan_intent: "",
    loan_grade: "B",
    cb_person_default_on_file: "",
  };

  const [formData, setFormData] = useState(emptyForm);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (initialData) {
      if (initialData.form_data) {
        setFormData({
          person_age: String(initialData.form_data.person_age || ""),
          person_income: String(initialData.form_data.person_income || ""),
          person_emp_length: String(initialData.form_data.person_emp_length || ""),
          loan_amnt: String(initialData.form_data.loan_amnt || ""),
          loan_int_rate: String(initialData.form_data.loan_int_rate || ""),
          loan_percent_income: String(initialData.form_data.loan_percent_income || ""),
          cb_person_cred_hist_length: String(initialData.form_data.cb_person_cred_hist_length || ""),
          person_home_ownership: initialData.form_data.person_home_ownership || "",
          loan_intent: initialData.form_data.loan_intent || "",
          loan_grade: initialData.form_data.loan_grade || "B",
          cb_person_default_on_file: initialData.form_data.cb_person_default_on_file || "",
        });
        setCurrentProfile(`Geçmiş Kayıt: ${initialData.customer_id || ''}`);
        if (initialData.customer_id) {
          setTckn(initialData.customer_id);
        }
      }
      setResult(null);
      setShapData([]);
      if (onLoaded) onLoaded();
    }
  }, [initialData, onLoaded]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setCurrentProfile("Manuel Giriş");
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSelectChange = (name: string, value: string) => {
    setCurrentProfile("Manuel Giriş");
    setFormData({ ...formData, [name]: value });
  };

  const clearForm = () => {
    setFormData(emptyForm);
    setResult(null);
    setShapData([]);
    setFraudRisk(null);
    setCurrentProfile("Yok");
    setError("");
    setActiveTool("none");
  };

  const handleRandomFill = () => {
    setCurrentProfile("Rastgele");
    setFormData({
      person_age: (Math.floor(Math.random() * 40) + 20).toString(),
      person_income: (Math.floor(Math.random() * 120000) + 30000).toString(),
      person_emp_length: (Math.floor(Math.random() * 15)).toString(),
      loan_amnt: (Math.floor(Math.random() * 30000) + 5000).toString(),
      loan_int_rate: (Math.floor(Math.random() * 15) + 5).toString(),
      loan_percent_income: (Math.random() * 0.4 + 0.1).toFixed(2),
      cb_person_cred_hist_length: (Math.floor(Math.random() * 10) + 1).toString(),
      person_home_ownership: ["RENT", "OWN", "MORTGAGE"][Math.floor(Math.random() * 3)],
      loan_intent: ["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE"][Math.floor(Math.random() * 4)],
      loan_grade: ["A", "B", "C", "D"][Math.floor(Math.random() * 4)],
      cb_person_default_on_file: Math.random() > 0.8 ? "Y" : "N",
    });
  };

  const handleAutoFill = (riskLevel: 'low' | 'mid' | 'high') => {
    if (riskLevel === 'low') {
      setCurrentProfile("Düşük Risk");
      setFormData({
        person_age: "45", person_income: "120000", person_emp_length: "15",
        loan_amnt: "10000", loan_int_rate: "7.5", loan_percent_income: "0.08",
        cb_person_cred_hist_length: "12", person_home_ownership: "OWN",
        loan_intent: "HOMEIMPROVEMENT", loan_grade: "A", cb_person_default_on_file: "N",
      });
    } else if (riskLevel === 'mid') {
      setCurrentProfile("Orta Risk");
      setFormData({
        person_age: "32", person_income: "65000", person_emp_length: "4",
        loan_amnt: "15000", loan_int_rate: "12.5", loan_percent_income: "0.23",
        cb_person_cred_hist_length: "6", person_home_ownership: "RENT",
        loan_intent: "PERSONAL", loan_grade: "C", cb_person_default_on_file: "N",
      });
    } else {
      setCurrentProfile("Yüksek Risk");
      setFormData({
        person_age: "24", person_income: "35000", person_emp_length: "1",
        loan_amnt: "20000", loan_int_rate: "18.5", loan_percent_income: "0.57",
        cb_person_cred_hist_length: "2", person_home_ownership: "RENT",
        loan_intent: "VENTURE", loan_grade: "E", cb_person_default_on_file: "Y",
      });
    }
  };

  const handleTcknSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tckn || tckn.length !== 11) {
      setTcknError("Lütfen 11 haneli geçerli bir TCKN giriniz.");
      return;
    }
    
    setIsSearchingTckn(true);
    setTcknError("");
    
    try {
      const data = await fetchCustomerData(tckn);
      setFormData({
        person_age: String(data.person_age),
        person_income: String(data.person_income),
        person_emp_length: String(data.person_emp_length),
        loan_amnt: String(data.loan_amnt),
        loan_int_rate: String(data.loan_int_rate),
        loan_percent_income: String(data.loan_percent_income),
        cb_person_cred_hist_length: String(data.cb_person_cred_hist_length),
        person_home_ownership: data.person_home_ownership,
        loan_intent: data.loan_intent,
        loan_grade: data.loan_grade,
        cb_person_default_on_file: data.cb_person_default_on_file,
      });
      setCurrentProfile(`TCKN: ${tckn} (Mock API)`);
    } catch (err: any) {
      setTcknError(err.message || "Müşteri verisi bulunamadı.");
    } finally {
      setIsSearchingTckn(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError(""); setResult(null); setShapData([]);
    
    try {
      const res = await evaluateCredit(formData as any);
      
      const normalizedResult = {
        ...res,
        decision: res.tahmin === 'ONAYLANDI' ? 'Approved' : 'Rejected',
        onay_olasiligi: Math.min(0.999, Math.max(0.001, res.onay_olasiligi ?? 0)),
      };
      
      setResult(normalizedResult);
      
      if (normalizedResult.decision) {
        if (normalizedResult.shap_top_features && normalizedResult.shap_top_features.length > 0) {
          setShapData(normalizedResult.shap_top_features.map((f: any) => ({
            feature: f.feature,
            impact: f.contribution,
            value: (formData as any)[f.feature]
          })));
        } else {
          setShapData([
            { feature: 'Yıllık Gelir', value: normalizedResult.decision === 'Approved' ? 0.8 : -0.5 },
            { feature: 'Kredi Miktarı', value: normalizedResult.decision === 'Approved' ? 0.3 : -0.7 },
            { feature: 'Kredi / Gelir Oranı', value: normalizedResult.decision === 'Approved' ? 0.5 : -0.9 },
            { feature: 'Çalışma Süresi', value: 0.2 },
            { feature: 'Kredi Geçmişi', value: 0.1 },
          ]);
        }
        
        if (normalizedResult.fraud_analysis) {
          setFraudRisk(normalizedResult.fraud_analysis.score);
        } else {
          setFraudRisk(normalizedResult.fraud_risk ?? Math.floor(Math.random() * 15) + 1);
        }
      }
    } catch (err: any) {
      setError(err.message || "Değerlendirme sırasında bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex flex-col xl:flex-row gap-6 w-full relative min-h-[calc(100vh-200px)]">
        
        {/* FORM SECTION */}
        <div className="flex-1 min-w-0 space-y-6">
          <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm print:hidden">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-1">Kredi Başvurusu</h2>
                {!result && <p className="text-slate-500 dark:text-slate-400 text-sm">Müşteri verilerini girerek anında yapay zeka destekli analiz yapın.</p>}
              </div>
              <div className="flex items-center gap-2">
                <button aria-label="Yeni Başvuru" onClick={clearForm} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition">
                  <Eraser size={16} /> Yeni Başvuru
                </button>
              </div>
            </div>
            
            {/* TCKN SEARCH BAR */}
            <div className="bg-slate-50 dark:bg-dark-900 p-4 rounded-xl border border-slate-200 dark:border-dark-700 mt-2 mb-4">
              <form onSubmit={handleTcknSearch} className="flex flex-col sm:flex-row gap-3 items-end sm:items-center">
                <div className="flex-1 w-full relative">
                  <label htmlFor="tckn" className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">
                    TCKN / Müşteri ID ile Sorgula
                  </label>
                  <input
                    type="text"
                    id="tckn"
                    value={tckn}
                    onChange={(e) => setTckn(e.target.value.replace(/\D/g, '').slice(0, 11))}
                    placeholder="Örn: 12345678900"
                    className="w-full px-4 py-2.5 rounded-lg bg-white dark:bg-dark-800 border border-slate-300 dark:border-dark-600 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none text-slate-800 dark:text-white"
                  />
                  {tcknError && <span className="text-rose-500 text-xs absolute -bottom-5 left-0">{tcknError}</span>}
                </div>
                <button
                  type="submit"
                  disabled={isSearchingTckn}
                  className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2 h-[42px] min-w-[140px] whitespace-nowrap disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {isSearchingTckn ? <Loader2 className="animate-spin" size={18} /> : "Sorgula (KKB)"}
                </button>
              </form>
            </div>
            
            {!result && (
              <div className="flex flex-wrap items-center gap-3 bg-slate-50 dark:bg-dark-900 p-4 rounded-xl border border-slate-100 dark:border-dark-700 mt-4">
                <div className="flex items-center gap-2 mr-4 border-r border-slate-200 dark:border-dark-700 pr-4">
                  <span className="text-sm text-slate-500">Profil:</span>
                  <span className="text-sm font-bold text-brand-600 truncate max-w-[90px]" title={currentProfile}>{currentProfile}</span>
                  <button aria-label="Bilgi Kılavuzunu Aç" onClick={() => setIsGuideOpen(true)} className="text-slate-400 hover:text-brand-500 transition">
                    <Info size={16} />
                  </button>
                </div>

                <button aria-label="Formu Rastgele Doldur" type="button" onClick={handleRandomFill} className="flex items-center gap-1.5 px-2 py-1.5 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-lg text-sm font-medium hover:bg-brand-100 dark:hover:bg-brand-900/40 transition">
                   <Wand2 size={14} /> Otomatik Doldur
                </button>
                <button type="button" onClick={() => handleAutoFill('low')} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-lg text-sm font-medium hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition">
                   Düşük Risk
                </button>
                <button type="button" onClick={() => handleAutoFill('mid')} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg text-sm font-medium hover:bg-blue-100 dark:hover:bg-blue-900/40 transition">
                   Orta Risk
                </button>
                <button type="button" onClick={() => handleAutoFill('high')} className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-lg text-sm font-medium hover:bg-rose-100 dark:hover:bg-rose-900/40 transition">
                   Yüksek Risk
                </button>
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm space-y-8 print:border-none print:shadow-none print:p-0">
            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <User size={20} className="text-brand-500" /> Kişisel & Finansal Bilgiler
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label htmlFor="person_age" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yaş</label>
                  <input type="number" name="person_age" value={formData.person_age} onChange={handleChange} id="person_age" min="18" max="100" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yıllık Gelir (TRY)</label>
                  <input type="number" name="person_income" value={formData.person_income} onChange={handleChange} id="person_income" min="0" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Çalışma Süresi (Yıl)</label>
                  <input type="number" name="person_emp_length" value={formData.person_emp_length} onChange={handleChange} id="person_emp_length" min="0" max="60" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label htmlFor="person_home_ownership" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ev Sahipliği</label>
                  <CustomSelect
                    id="person_home_ownership"
                    name="person_home_ownership"
                    value={formData.person_home_ownership}
                    onChange={(val) => handleSelectChange('person_home_ownership', val)}
                    placeholder="Bir seçenek belirleyin..."
                    options={[
                      { value: "RENT", label: "Kira (RENT)" },
                      { value: "OWN", label: "Ev Sahibi (OWN)" },
                      { value: "MORTGAGE", label: "İpotekli (MORTGAGE)" },
                      { value: "OTHER", label: "Diğer (OTHER)" }
                    ]}
                  />
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <AlertCircle size={20} className="text-brand-500" /> Kredi & Geçmiş Detayları
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label htmlFor="loan_amnt" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Tutarı</label>
                  <input type="number" name="loan_amnt" value={formData.loan_amnt} onChange={handleChange} id="loan_amnt" min="100" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Faiz Oranı (%)</label>
                  <input type="number" step="0.1" name="loan_int_rate" value={formData.loan_int_rate} onChange={handleChange} id="loan_int_rate" min="0" max="100" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Geçmişi (Yıl)</label>
                  <input type="number" name="cb_person_cred_hist_length" value={formData.cb_person_cred_hist_length} onChange={handleChange} id="cb_person_cred_hist_length" min="0" max="60" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi / Gelir Oranı (DTI)</label>
                  <input type="number" step="0.01" name="loan_percent_income" value={formData.loan_percent_income} onChange={handleChange} id="loan_percent_income" min="0.01" max="1" required className="w-full px-4 py-2 rounded-xl bg-slate-50 dark:bg-dark-900 border border-slate-200 dark:border-dark-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none print:bg-white print:border-gray-300" />
                </div>
                <div>
                  <label htmlFor="loan_intent" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kredi Amacı</label>
                  <CustomSelect
                    id="loan_intent"
                    name="loan_intent"
                    value={formData.loan_intent}
                    onChange={(val) => handleSelectChange('loan_intent', val)}
                    placeholder="Bir seçenek belirleyin..."
                    options={[
                      { value: "PERSONAL", label: "Kişisel" },
                      { value: "EDUCATION", label: "Eğitim" },
                      { value: "MEDICAL", label: "Sağlık" },
                      { value: "VENTURE", label: "Girişim" },
                      { value: "HOMEIMPROVEMENT", label: "Ev Geliştirme" },
                      { value: "DEBTCONSOLIDATION", label: "Borç Kapatma" }
                    ]}
                  />
                </div>
                <div>
                  <label htmlFor="cb_person_default_on_file" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Geçmiş Temerrüt</label>
                  <CustomSelect
                    id="cb_person_default_on_file"
                    name="cb_person_default_on_file"
                    value={formData.cb_person_default_on_file}
                    onChange={(val) => handleSelectChange('cb_person_default_on_file', val)}
                    placeholder="Bir seçenek belirleyin..."
                    options={[
                      { value: "N", label: "Hayır" },
                      { value: "Y", label: "Evet" }
                    ]}
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 rounded-xl flex items-center gap-3 print:hidden">
                <AlertCircle size={20} />
                <p>{error}</p>
              </div>
            )}

            <div className="pt-4 border-t border-slate-200 dark:border-dark-700 print:hidden">
              <button type="submit" disabled={loading} className="w-full px-8 py-4 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-bold text-lg transition-transform hover:-translate-y-1 shadow-lg shadow-brand-500/30 flex items-center justify-center group">
                {loading ? <Loader2 className="animate-spin mr-3" size={24} /> : <Sparkles className="mr-3 group-hover:scale-125 transition-transform" size={24} />}
                Yapay Zeka İle Risk Analizi Yap
              </button>
            </div>
          </form>
        </div>

        {/* RIGHT COLUMN / BOTTOM RESULTS */}
        <div className={`w-full ${result ? 'xl:w-[440px] xl:flex-shrink-0' : 'xl:w-[380px] xl:flex-shrink-0'} flex flex-col gap-6 transition-all duration-500`} id="result-wrapper">
          {!result && (
            <div className="h-full bg-slate-50 dark:bg-dark-900/50 rounded-2xl border-2 border-dashed border-slate-200 dark:border-dark-700 flex flex-col items-center justify-center p-8 text-center text-slate-400 print:hidden">
              <BrainCircuit size={64} className="mb-4 opacity-30" />
              <h3 className="text-xl font-bold text-slate-600 dark:text-slate-300 mb-2">Analiz Bekleniyor</h3>
              <p className="text-sm">Sol taraftaki formu doldurun ve sonucu burada detaylıca inceleyin.</p>
            </div>
          )}

          {result && (
            <ResultPanel 
              result={result} 
              shapData={shapData} 
              fraudRisk={fraudRisk} 
              activeTool={activeTool} 
              setActiveTool={setActiveTool} 
              formData={formData} 
            />
          )}
        </div>

        <AiChatWidget result={result} formData={formData} />

        {/* PROFILE GUIDE MODAL */}
        {isGuideOpen && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4 print:hidden">
            <div className="bg-white dark:bg-dark-800 w-full max-w-lg rounded-2xl shadow-xl overflow-hidden animate-in zoom-in-95 duration-200">
              <div className="flex justify-between items-center p-6 border-b border-slate-100 dark:border-dark-700">
                <h3 className="font-bold text-lg text-slate-800 dark:text-white flex items-center gap-2">
                  <Info className="text-brand-500" /> Profil Üretim Rehberi
                </h3>
                <button aria-label="Kılavuzu Kapat" onClick={() => setIsGuideOpen(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-white">
                  Kapat
                </button>
              </div>
              <div className="p-6 space-y-4 text-sm text-slate-600 dark:text-slate-300">
                <p>
                  Simülatör modüllerimiz, gerçek veri seti istatistiklerine dayanan **sentetik (suni) profiller** üretir. Bu profiller modelin sınırlarını test etmeniz için tasarlanmıştır:
                </p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-emerald-500 flex-shrink-0"></div>
                    <div><strong className="text-emerald-600 dark:text-emerald-400">Düşük Risk:</strong> Yüksek gelir, uzun kredi geçmişi ve sıfır temerrüt. Modelin %95+ olasılıkla Onay vermesi beklenir.</div>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-blue-500 flex-shrink-0"></div>
                    <div><strong className="text-blue-600 dark:text-blue-400">Orta Risk:</strong> Ortalama gelir ve borç oranı. Kredi amacı (örn: Kişisel) gibi parametrelerin modele etkisini görmek için idealdir. (Sınır vaka)</div>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-rose-500 flex-shrink-0"></div>
                    <div><strong className="text-rose-600 dark:text-rose-400">Yüksek Risk:</strong> Kısa çalışma süresi, yüksek DTI (Borç/Gelir) oranı ve geçmiş temerrüt izi. Reddedilme senaryolarını test eder.</div>
                  </li>
                </ul>
              </div>
              <div className="bg-slate-50 dark:bg-dark-900 p-4 border-t border-slate-100 dark:border-dark-700 flex justify-end">
                <button onClick={() => setIsGuideOpen(false)} className="px-6 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-dark-700 dark:hover:bg-dark-600 text-slate-800 dark:text-white rounded-lg font-medium transition">
                  Anladım
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <footer className="mt-8 pt-8 pb-4 border-t border-slate-200 dark:border-dark-700 text-center w-full clear-both">
        <p className="text-[11px] text-slate-500 dark:text-slate-400 max-w-3xl mx-auto leading-relaxed">
          <strong className="text-slate-600 dark:text-slate-300">Yasal Bilgilendirme:</strong> FinWise ML platformu tarafından sunulan analiz sonuçları, kredi skorları ve sahtekarlık (fraud) tahminleri yapay zeka tabanlı bir karar destek sisteminin çıktılarıdır. Bu sonuçlar kesin hüküm niteliği taşımaz ve yasal bir dayanak olarak kullanılamaz. Nihai kredi değerlendirme ve onay kararları, bankaların kendi yasal süreçleri, iç politikaları ve güncel BDDK mevzuatları çerçevesinde verilmelidir.
        </p>
        <div className="mt-4 flex items-center justify-center gap-4 text-[10px] text-slate-400 dark:text-slate-500">
          <span>© 2026 FinWise Inc.</span>
          <span>•</span>
          <a href="#" className="hover:text-brand-500 transition-colors">Gizlilik Politikası</a>
          <span>•</span>
          <a href="#" className="hover:text-brand-500 transition-colors">Kullanım Şartları</a>
        </div>
      </footer>
    </>
  );
}
