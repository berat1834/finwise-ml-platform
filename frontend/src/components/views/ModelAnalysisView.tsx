import React from "react";
import { Activity, ShieldCheck, Database, BrainCircuit, BarChart } from "lucide-react";

export default function ModelAnalysisView() {
  return (
    <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm animate-in fade-in slide-in-from-bottom-4">
      <div className="mb-6 border-b border-slate-200 dark:border-dark-700 pb-4">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <BrainCircuit className="text-brand-500" /> Model Analizi (v2.6)
        </h2>
        <p className="text-slate-500 dark:text-slate-400 mt-1">Canlı ortamda çalışan XGBoost modelinin performans ve adillik metrikleri.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-slate-50 dark:bg-dark-900 p-5 rounded-xl border border-slate-100 dark:border-dark-700">
          <div className="flex items-center gap-2 mb-3 text-slate-700 dark:text-slate-300 font-bold">
            <Activity className="text-blue-500" size={18} /> Doğruluk (Accuracy)
          </div>
          <div className="text-3xl font-black text-slate-900 dark:text-white mb-2">%94.2</div>
          <div className="w-full bg-slate-200 dark:bg-dark-700 h-2 rounded-full overflow-hidden">
            <div className="bg-blue-500 h-full" style={{ width: '94.2%' }}></div>
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-dark-900 p-5 rounded-xl border border-slate-100 dark:border-dark-700">
          <div className="flex items-center gap-2 mb-3 text-slate-700 dark:text-slate-300 font-bold">
            <BarChart className="text-emerald-500" size={18} /> F1 Skoru
          </div>
          <div className="text-3xl font-black text-slate-900 dark:text-white mb-2">0.91</div>
          <div className="w-full bg-slate-200 dark:bg-dark-700 h-2 rounded-full overflow-hidden">
            <div className="bg-emerald-500 h-full" style={{ width: '91%' }}></div>
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-dark-900 p-5 rounded-xl border border-slate-100 dark:border-dark-700">
          <div className="flex items-center gap-2 mb-3 text-slate-700 dark:text-slate-300 font-bold">
            <ShieldCheck className="text-amber-500" size={18} /> Adillik Oranı (DI Ratio)
          </div>
          <div className="text-3xl font-black text-slate-900 dark:text-white mb-2">0.85</div>
          <div className="w-full bg-slate-200 dark:bg-dark-700 h-2 rounded-full overflow-hidden">
            <div className="bg-amber-500 h-full" style={{ width: '85%' }}></div>
          </div>
          <p className="text-xs text-slate-500 mt-2">80% kuralının üzerinde, güvenli bölge.</p>
        </div>
      </div>
      
      <div className="mt-8 bg-brand-50 dark:bg-brand-900/20 p-6 rounded-xl border border-brand-100 dark:border-brand-900/30">
        <h3 className="font-bold text-brand-800 dark:text-brand-300 mb-2 flex items-center gap-2">
          <Database size={18} /> Veri Seti Bilgisi
        </h3>
        <p className="text-sm text-brand-700 dark:text-brand-400">
          Model en son <strong>01.08.2026</strong> tarihinde <strong>124,500</strong> adet başvuru kaydı üzerinden eğitilmiştir. Gecikme (latency) ortalaması 120ms seviyesindedir.
        </p>
      </div>
    </div>
  );
}
