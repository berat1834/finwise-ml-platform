import React, { useState } from 'react';
import { Settings2, Loader2, Wand2 } from 'lucide-react';

export default function ScenarioSimulator({ result }: { result: any }) {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [scenariosLoading, setScenariosLoading] = useState(false);

  const generateScenarios = () => {
    if (!result) return;
    setScenariosLoading(true);
    setTimeout(() => {
      setScenarios([
        {
          description: "Kredi miktarını 5000 azalt",
          approval_probability_delta: 0.15,
          simulated: { onay_olasiligi: Math.min(0.999, result.onay_olasiligi + 0.15) }
        },
        {
          description: "Geliri %20 daha yüksek beyan et",
          approval_probability_delta: 0.08,
          simulated: { onay_olasiligi: Math.min(0.999, result.onay_olasiligi + 0.08) }
        },
        {
          description: "Kredi geçmişini (yıl) 3 yıl uzat",
          approval_probability_delta: 0.12,
          simulated: { onay_olasiligi: Math.min(0.999, result.onay_olasiligi + 0.12) }
        }
      ]);
      setScenariosLoading(false);
    }, 1000);
  };

  return (
    <div id="simulator-section" className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-blue-200 dark:border-blue-900/50 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
      <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
        <Settings2 className="text-blue-500" size={16} /> Onay Simülatörü
      </h3>
      
      {scenarios.length > 0 ? (
        <div className="space-y-3">
          {scenarios.map((sc, i) => (
            <div key={i} className="bg-slate-50 dark:bg-dark-900 p-3 rounded-xl border border-slate-200 dark:border-dark-700">
              <p className="font-medium text-slate-800 dark:text-white text-xs mb-2">{sc.description}</p>
              <div className="flex justify-between items-center mt-2">
                <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-1 rounded">+{ (sc.approval_probability_delta * 100).toFixed(1) }%</span>
                <span className="text-xs font-bold text-brand-600">%{(sc.simulated.onay_olasiligi * 100).toFixed(1)} Tahmin</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-6">
          <p className="text-xs text-slate-500 mb-4">Mevcut başvurunun onay şansını artırmak veya şartlarını optimize etmek için senaryo üretin.</p>
          <button onClick={generateScenarios} disabled={scenariosLoading} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-xs transition flex items-center justify-center gap-2 mx-auto">
            {scenariosLoading ? <Loader2 className="animate-spin" size={14} /> : <Wand2 size={14} />} 
            Senaryo Üret
          </button>
        </div>
      )}
    </div>
  );
}
