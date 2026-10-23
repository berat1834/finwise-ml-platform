"use client";

import React, { useEffect, useState } from "react";
import { 
  Activity, 
  ShieldCheck, 
  BrainCircuit, 
  RefreshCw, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  Info,
  Sliders,
  Sparkles
} from "lucide-react";
import { getModelDrift, recalculateModelDrift } from "@/lib/api";
import { DriftAnalysisResponse } from "@/types";

const FEATURE_NAMES_TR: Record<string, string> = {
  person_age: "Yaş (person_age)",
  person_income: "Yıllık Gelir (person_income)",
  person_emp_length: "İstihdam Süresi (person_emp_length)",
  loan_amnt: "Kredi Tutarı (loan_amnt)",
  loan_int_rate: "Faiz Oranı (loan_int_rate)",
  loan_percent_income: "Borç / Gelir Oranı (loan_percent_income)",
  cb_person_cred_hist_length: "Kredi Geçmişi (cb_person_cred_hist_length)",
  person_home_ownership: "Konut Durumu (person_home_ownership)",
  loan_intent: "Kredi Amacı (loan_intent)",
  loan_grade: "Kredi Derecesi (loan_grade)",
  cb_person_default_on_file: "Geçmiş Temerrüt (cb_person_default_on_file)",
};

export default function ModelAnalysisView() {
  const [driftData, setDriftData] = useState<DriftAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [recalculating, setRecalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      try {
        setError(null);
        const data = await getModelDrift(500);
        if (!ignore) setDriftData(data);
      } catch (err: unknown) {
        if (!ignore) {
          const message = err instanceof Error ? err.message : "Model drift analizi yüklenirken hata oluştu.";
          setError(message);
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, []);

  const handleRecalculate = async () => {
    try {
      setRecalculating(true);
      setError(null);
      setSuccessMessage(null);
      const res = await recalculateModelDrift();
      setDriftData(res.data);
      setSuccessMessage("Popülasyon kayması (PSI) analizi güncel canlı başvurular üzerinden başarıyla yeniden hesaplandı!");
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Yeniden hesaplama başarısız oldu.";
      setError(message);
    } finally {
      setRecalculating(false);
    }
  };

  const getStatusBadge = (status: string, psi: number) => {
    if (status === "CRITICAL" || psi >= 0.25) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400">
          <AlertTriangle size={12} /> Kritik Sapma ({psi.toFixed(3)})
        </span>
      );
    }
    if (status === "WARNING" || psi >= 0.10) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
          <TrendingUp size={12} /> Dikkat ({psi.toFixed(3)})
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
        <CheckCircle2 size={12} /> Stabil ({psi.toFixed(3)})
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Top Banner */}
      <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 bg-brand-500/10 text-brand-500 rounded-xl">
              <BrainCircuit size={26} />
            </div>
            <div>
              <h2 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">
                Model Drift & Popülasyon Kayması (PSI) İzleme
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Canlı ortamdaki kredi başvurularının eğitim veri seti dağılımına göre sapma analizi (Population Stability Index).
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={handleRecalculate}
          disabled={recalculating || loading}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold text-sm rounded-xl transition-all shadow-sm active:scale-95"
        >
          <RefreshCw size={16} className={recalculating ? "animate-spin" : ""} />
          {recalculating ? "Hesaplanıyor..." : "Şimdi Yeniden Hesapla"}
        </button>
      </div>

      {successMessage && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl text-emerald-800 dark:text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 size={18} />
          {successMessage}
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl text-rose-800 dark:text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="p-16 text-center bg-white dark:bg-dark-800 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
          <RefreshCw className="animate-spin mx-auto text-brand-500 mb-4" size={32} />
          <p className="text-slate-600 dark:text-slate-300 font-medium">Popülasyon dağılımları ve PSI testleri hesaplanıyor...</p>
        </div>
      ) : driftData ? (
        <>
          {/* Sample Size Guidance Banner if N < 100 */}
          {driftData.sample_warning_message && (
            <div className="p-4 bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-800 rounded-xl text-sky-800 dark:text-sky-300 text-sm flex items-start gap-3">
              <Info size={18} className="shrink-0 mt-0.5 text-sky-500" />
              <div>
                <span className="font-semibold">İstatistiki Güvenilirlik Notu: </span>
                {driftData.sample_warning_message}
              </div>
            </div>
          )}

          {/* Executive Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

            <div className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Genel Popülasyon PSI
                </span>
                <Activity size={18} className="text-brand-500" />
              </div>
              <div className="text-3xl font-black text-slate-900 dark:text-white mb-2">
                {driftData.overall_psi.toFixed(4)}
              </div>
              <div className="w-full bg-slate-100 dark:bg-dark-700 h-2.5 rounded-full overflow-hidden mb-2">
                <div 
                  className={`h-full transition-all duration-500 ${
                    driftData.overall_psi < 0.10 ? "bg-emerald-500" : driftData.overall_psi < 0.25 ? "bg-amber-500" : "bg-rose-500"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(10, driftData.overall_psi * 300))}%` }}
                />
              </div>
              <div className="text-xs text-slate-500">
                {driftData.overall_psi < 0.10 ? "Normal sınır (< 0.10)" : "İzleme tavsiye edilir"}
              </div>
            </div>

            <div className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Model Kararlılık Durumu
                </span>
                <ShieldCheck size={18} className="text-emerald-500" />
              </div>
              <div className="text-2xl font-black mb-2">
                {driftData.overall_status === "STABLE" && (
                  <span className="text-emerald-600 dark:text-emerald-400">STABİL</span>
                )}
                {driftData.overall_status === "MODERATE_DRIFT" && (
                  <span className="text-amber-600 dark:text-amber-400">ORTA KAYMA</span>
                )}
                {driftData.overall_status === "CRITICAL_DRIFT" && (
                  <span className="text-rose-600 dark:text-rose-400">KRİTİK KAYMA</span>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Maksimum özellik sapması: <strong>{driftData.max_feature_psi.toFixed(3)}</strong>
              </p>
            </div>

            <div className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Sapma Gösteren Alanlar
                </span>
                <AlertTriangle size={18} className="text-amber-500" />
              </div>
              <div className="text-3xl font-black text-slate-900 dark:text-white mb-2">
                {driftData.drifted_features_count} / {driftData.total_evaluated_features}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {driftData.drifted_features_count === 0 ? "Hiçbir özellikte sapma yok" : "Sapma tespit edilen değişkenler"}
              </p>
            </div>

            <div className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  İnceleme Penceresi
                </span>
                <Sliders size={18} className="text-indigo-500" />
              </div>
              <div className="text-3xl font-black text-slate-900 dark:text-white mb-2">
                {driftData.evaluation_window_size}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Canlı DB Başvuru: <strong>{driftData.total_live_applications_in_db}</strong>
              </p>
            </div>
          </div>

          {/* Diagnostic Summary & Actionable Recommendations */}
          <div className="bg-brand-50/60 dark:bg-brand-950/20 p-6 rounded-2xl border border-brand-200/60 dark:border-brand-900/40 shadow-sm">
            <h3 className="font-bold text-brand-900 dark:text-brand-200 mb-2 flex items-center gap-2">
              <Sparkles size={18} className="text-brand-600 dark:text-brand-400" />
              FinWise Drift Analiz Özeti & Önerilen Aksiyonlar
            </h3>
            <p className="text-sm text-brand-800 dark:text-brand-300 mb-3">
              {driftData.summary_message}
            </p>
            <ul className="space-y-1.5 text-xs text-brand-700 dark:text-brand-400 list-disc list-inside">
              {driftData.recommendations.map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </div>

          {/* Feature-Level Drift Table */}
          <div className="bg-white dark:bg-dark-800 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-200 dark:border-dark-700 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="font-bold text-slate-800 dark:text-white text-base">
                  Değişken Bazında Kararlılık Analizi (Feature PSI / CSI Breakdown)
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Eğitim referansı ile canlı müşteri profilleri arasındaki dağılım karşılaştırması
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-1 text-slate-500">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> &lt;0.10 Stabil
                </span>
                <span className="flex items-center gap-1 text-slate-500">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> 0.10-0.25 Orta
                </span>
                <span className="flex items-center gap-1 text-slate-500">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> &gt;0.25 Kritik
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                <thead className="bg-slate-50 dark:bg-dark-900 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-dark-700">
                  <tr>
                    <th className="px-5 py-3.5">Değişken Adı</th>
                    <th className="px-5 py-3.5">Tür</th>
                    <th className="px-5 py-3.5">PSI / CSI Skoru</th>
                    <th className="px-5 py-3.5">Referans Değer</th>
                    <th className="px-5 py-3.5">Canlı Değer</th>
                    <th className="px-5 py-3.5 text-right">Durum</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-dark-700">
                  {Object.entries(driftData.features).map(([key, metric]) => {
                    const label = FEATURE_NAMES_TR[key] || key;
                    return (
                      <tr key={key} className="hover:bg-slate-50/80 dark:hover:bg-dark-750 transition-colors">
                        <td className="px-5 py-3.5 font-semibold text-slate-800 dark:text-white">
                          {label}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-dark-700 text-slate-600 dark:text-slate-400 font-medium">
                            {metric.type === "numeric" ? "Sayısal" : "Kategorik"}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 font-mono font-bold">
                          {metric.psi.toFixed(4)}
                        </td>
                        <td className="px-5 py-3.5 text-slate-500 text-xs">
                          {metric.type === "numeric" && metric.baseline_mean !== undefined
                            ? `Ort: ${metric.baseline_mean.toLocaleString("tr-TR")}`
                            : metric.top_baseline_category
                            ? `Mod: ${metric.top_baseline_category}`
                            : "-"}
                        </td>
                        <td className="px-5 py-3.5 text-slate-700 dark:text-slate-300 text-xs font-medium">
                          {metric.type === "numeric" && metric.current_mean !== undefined
                            ? `Ort: ${metric.current_mean.toLocaleString("tr-TR")}`
                            : metric.top_current_category
                            ? `Mod: ${metric.top_current_category}`
                            : "-"}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          {getStatusBadge(metric.status, metric.psi)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Regulatory & Methodology Information */}
          <div className="bg-slate-50 dark:bg-dark-900 p-5 rounded-2xl border border-slate-200 dark:border-dark-700 text-xs text-slate-500 dark:text-slate-400 flex items-start gap-3">
            <Info size={18} className="text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Metodoloji & BDDK / Basel II Bankacılık Standartları
              </p>
              <p>
                Population Stability Index (PSI), kredi tahsis modellerinde girdi değişkenlerinin ve skor dağılımlarının zaman içerisindeki kaymasını ölçmek için uluslararası bankacılıkta zorunlu kabul edilen standart metriktir. PSI &lt; 0.10 popülasyonun stabil olduğunu, 0.10 - 0.25 arası hafif sapma olduğunu, 0.25 ve üzeri değerler ise modelin geçmiş risk profilini temsil etmekte yetersiz kaldığını ve acil yeniden eğitim (retraining) gerektiğini gösterir.
              </p>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
