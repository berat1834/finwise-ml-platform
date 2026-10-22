"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[FinWise Error]", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white dark:bg-dark-800 rounded-2xl p-8 shadow-premium border border-slate-200 dark:border-dark-700 text-center">
        <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="text-red-600 dark:text-red-400" size={32} />
        </div>
        
        <h2 className="text-2xl font-heading font-bold text-slate-800 dark:text-white mb-2">
          Bir Hata Oluştu
        </h2>
        <p className="text-slate-500 dark:text-slate-400 mb-6">
          Beklenmeyen bir hata meydana geldi. Lütfen tekrar deneyin veya sorun devam ederse destek ekibiyle iletişime geçin.
        </p>
        
        {error.digest && (
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-4 font-mono">
            Hata Kodu: {error.digest}
          </p>
        )}
        
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 px-6 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-medium transition-all shadow-md"
        >
          <RefreshCw size={18} />
          Tekrar Dene
        </button>
      </div>
    </div>
  );
}
