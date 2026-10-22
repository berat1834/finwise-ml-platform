import React from "react";
import { FileText, Download, Calendar } from "lucide-react";

export default function ReportsView() {
  const reports = [
    { title: "Aylık Kredi Onay Performansı", date: "01 Ağustos 2026", type: "PDF", size: "2.4 MB" },
    { title: "Model Adillik (Fairness) Denetimi", date: "15 Temmuz 2026", type: "PDF", size: "1.8 MB" },
    { title: "Risk Segmentasyonu Dağılımı", date: "01 Temmuz 2026", type: "CSV", size: "4.1 MB" },
    { title: "Reddedilen Başvurular Analizi", date: "15 Haziran 2026", type: "PDF", size: "3.2 MB" },
  ];

  const handleDownload = (report: any) => {
    // Demo amacıyla sahte (mock) bir dosya içeriği oluşturuyoruz
    const content = `${report.title}\nTarih: ${report.date}\nBu dosya FinWise ML Platformu tarafından otomatik oluşturulmuştur.`;
    const blob = new Blob([content], { type: report.type === 'CSV' ? 'text/csv' : 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.replace(/\s+/g, '_').toLowerCase()}.${report.type.toLowerCase()}`;
    document.body.appendChild(a);
    a.click();
    
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm animate-in fade-in slide-in-from-bottom-4">
      <div className="mb-6 border-b border-slate-200 dark:border-dark-700 pb-4">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <FileText className="text-brand-500" /> Sistem Raporları
        </h2>
        <p className="text-slate-500 dark:text-slate-400 mt-1">Geçmiş dönem performans analizleri ve otomatik oluşturulan dokümanlar.</p>
      </div>

      <div className="space-y-4">
        {reports.map((report, idx) => (
          <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-slate-50 dark:bg-dark-900 rounded-xl border border-slate-100 dark:border-dark-700 hover:border-brand-300 dark:hover:border-brand-700 transition-colors">
            <div className="flex items-start gap-4 mb-3 sm:mb-0">
              <div className="p-3 bg-white dark:bg-dark-800 rounded-lg shadow-sm">
                <FileText className="text-brand-600 dark:text-brand-400" size={24} />
              </div>
              <div>
                <h4 className="font-bold text-slate-800 dark:text-white">{report.title}</h4>
                <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                  <span className="flex items-center gap-1"><Calendar size={12} /> {report.date}</span>
                  <span>•</span>
                  <span>{report.type}</span>
                  <span>•</span>
                  <span>{report.size}</span>
                </div>
              </div>
            </div>
            
            <button 
              onClick={() => handleDownload(report)}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-white dark:bg-dark-800 text-slate-700 dark:text-slate-300 font-medium text-sm rounded-lg border border-slate-200 dark:border-dark-700 hover:bg-slate-100 dark:hover:bg-dark-700 transition">
              <Download size={16} /> İndir
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
