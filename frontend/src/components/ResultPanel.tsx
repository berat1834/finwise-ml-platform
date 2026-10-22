import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  BarChart as BarChartIcon, 
  Download, 
  Settings2, 
  ShieldAlert, 
  Loader2, 
  FileText, 
  FileJson,
  Building2,
  ExternalLink,
  Sparkles,
  ChevronRight
} from 'lucide-react';
import ShapChart from './ShapChart';
import ScenarioSimulator from './ScenarioSimulator';
import { getBankOffers } from '@/lib/api';
import { BankOffer } from '@/types';

export default function ResultPanel({ 
  result, 
  shapData, 
  fraudRisk, 
  activeTool, 
  setActiveTool, 
  formData 
}: { 
  result: any; 
  shapData: any[]; 
  fraudRisk: number | null; 
  activeTool: string; 
  setActiveTool: (tool: any) => void; 
  formData: any; 
}) {
  const [downloadDropdownOpen, setDownloadDropdownOpen] = useState(false);
  const [offers, setOffers] = useState<BankOffer[]>([]);
  const [offersLoading, setOffersLoading] = useState(false);
  const [offersError, setOffersError] = useState("");
  const [selectedTerm, setSelectedTerm] = useState<number>(36);
  const [offerDisclaimer, setOfferDisclaimer] = useState("");
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  if (!result) return null;

  const fetchOffers = async (term = selectedTerm) => {
    const amount = parseFloat(formData?.loan_amnt) || 50000;
    setOffersLoading(true);
    setOffersError("");
    try {
      const risk = result?.red_olasiligi ?? (result?.onay_olasiligi ? 1 - result.onay_olasiligi : 0.2);
      const res = await getBankOffers({
        amount: amount,
        term_months: term,
        risk_score: risk,
        decision: result?.decision || (result?.fraud_analysis?.is_fraud ? "REDDEDİLDİ" : "Approved")
      });
      setOffers(res.offers || []);
      setOfferDisclaimer(res.disclaimer || "");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Banka teklifleri alınamadı.";
      setOffersError(msg);
    } finally {
      setOffersLoading(false);
    }
  };

  const handleTermChange = (newTerm: number) => {
    setSelectedTerm(newTerm);
    fetchOffers(newTerm);
  };

  const downloadExecutivePDF = async () => {
    const appId = result?.application_id;
    if (!appId) {
      window.print();
      return;
    }
    setDownloadingPdf(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";
      const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
      const res = await fetch(`${apiUrl}/api/v2/applications/${appId}/report/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("PDF indirilemedi");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FinWise_Kredi_Raporu_FW-${appId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
      window.print();
    } finally {
      setDownloadingPdf(false);
      setDownloadDropdownOpen(false);
    }
  };

  const downloadNativePDF = () => {
    window.print();
  };

  const downloadJSON = () => {
    if (!result) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ request: formData, response: result }, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `FinWise_Kredi_${new Date().getTime()}.json`);
    dlAnchorElem.click();
  };

  const downloadCSV = () => {
    if (!result) return;
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Özellik,Değer\n";
    Object.entries(formData).forEach(([key, val]) => {
      csvContent += `${key},${val}\n`;
    });
    csvContent += `Karar,${result.decision}\n`;
    csvContent += `Onay Olasılığı,${result.onay_olasiligi}\n`;
    
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", csvContent);
    dlAnchorElem.setAttribute("download", `FinWise_Kredi_${new Date().getTime()}.csv`);
    dlAnchorElem.click();
  };

  return (
    <div className="space-y-6 bg-slate-50 dark:bg-dark-900/30 p-2 rounded-2xl print:p-0 print:bg-transparent">
      {/* RESULT CARD (Always visible) */}
      <div className="bg-white dark:bg-dark-800 p-6 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm text-center relative print:border-gray-300 print:shadow-none">
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-200 dark:bg-dark-700 print:hidden"></div>
        
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">KARAR ÖZETİ</h3>
        </div>
        
        <div className="animate-in zoom-in duration-300">
          {result.fraud_analysis?.is_fraud ? (
            <div className="w-20 h-20 mx-auto bg-amber-100 dark:bg-amber-900/30 text-amber-500 rounded-full flex items-center justify-center mb-4 shadow-[0_0_40px_rgba(245,158,11,0.3)] print:shadow-none">
              <ShieldAlert size={40} />
            </div>
          ) : result.decision === "Approved" ? (
            <div className="w-20 h-20 mx-auto bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 rounded-full flex items-center justify-center mb-4 shadow-[0_0_40px_rgba(16,185,129,0.3)] print:shadow-none">
              <CheckCircle2 size={40} />
            </div>
          ) : (
            <div className="w-20 h-20 mx-auto bg-red-100 dark:bg-red-900/30 text-red-500 rounded-full flex items-center justify-center mb-4 shadow-[0_0_40px_rgba(239,68,68,0.3)] print:shadow-none">
              <AlertCircle size={40} />
            </div>
          )}
          
          <h2 className={`text-2xl font-black mb-1 ${result.fraud_analysis?.is_fraud ? 'text-amber-500' : result.decision === 'Approved' ? 'text-emerald-500' : 'text-red-500'}`}>
            {result.fraud_analysis?.is_fraud ? "REDDEDİLDİ (FRAUD)" : result.decision === "Approved" ? "ONAYLANDI" : "REDDEDİLDİ"}
          </h2>
          <div className="text-xs text-slate-500 font-medium">
            {result.fraud_analysis?.is_fraud ? "GÜVENLİK FİLTRESİ" : "MODEL KARARI"}
          </div>
          
          {result.fraud_analysis?.is_fraud ? (
            <div className="mt-6 space-y-4 text-left">
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800">
                <h4 className="font-bold text-amber-800 dark:text-amber-400 mb-2">Şüpheli İşlem (Anomali) Nedenleri:</h4>
                <ul className="list-disc pl-5 text-sm text-amber-700 dark:text-amber-500 space-y-1">
                  {result.fraud_analysis.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
                </ul>
              </div>
              <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-xl text-[11px] mt-4 border border-red-100 dark:border-red-900/30 print:hidden">
                <strong className="block mb-1">Uyarı:</strong> Başvuru resmi KKB ve veri doğrulama aşamasını geçemediği için değerlendirmeye alınmamıştır.
              </div>
            </div>
          ) : (
            <div className="mt-6 space-y-4 text-left">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Güven Skoru</span>
                  <span className="font-bold text-slate-900 dark:text-white">
                    %{(Math.max(result.onay_olasiligi, 1 - result.onay_olasiligi) * 100).toFixed(1)}
                  </span>
                </div>
                <div className="h-2 w-full bg-slate-200 dark:bg-dark-700 rounded-full overflow-hidden print:border print:border-gray-300">
                  <div className="h-full bg-brand-500 rounded-full transition-all duration-1000 print:bg-gray-400" style={{ width: `${Math.max(result.onay_olasiligi, 1 - result.onay_olasiligi) * 100}%` }}></div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-emerald-50 dark:bg-emerald-900/20 p-2 rounded-lg border border-emerald-100 dark:border-emerald-900/30 print:bg-white print:border-gray-200">
                  <div className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400">Onay Olasılığı</div>
                  <div className="font-bold text-emerald-700 dark:text-emerald-300">%{(result.onay_olasiligi * 100).toFixed(1)}</div>
                </div>
                <div className="bg-red-50 dark:bg-red-900/20 p-2 rounded-lg border border-red-100 dark:border-red-900/30 print:bg-white print:border-gray-200">
                  <div className="text-[10px] uppercase font-bold text-red-600 dark:text-red-400">Ret Olasılığı</div>
                  <div className="font-bold text-red-700 dark:text-red-300">%{(Math.max(0, (1 - result.onay_olasiligi)) * 100).toFixed(1)}</div>
                </div>
              </div>
              
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 rounded-xl text-[11px] mt-4 border border-amber-100 dark:border-amber-900/30 print:hidden">
                <strong className="block mb-1">Bilgilendirme:</strong> Bu sonuç karar destek amaçlıdır; nihai karar bankanın yasal sürecinde verilir.
              </div>
            </div>
          )}
        </div>

        {/* ACTION TOOLBAR */}
        <button 
          onClick={() => {
            if (activeTool !== 'quote') {
              fetchOffers();
              setTimeout(() => {
                document.getElementById('quote-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }, 100);
            }
            setActiveTool(activeTool === 'quote' ? 'none' : 'quote');
          }}
          className={`w-full py-3 rounded-xl font-bold text-sm flex justify-center items-center gap-2 mb-4 transition-all ${activeTool === 'quote' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-dark-800 text-brand-600 border-2 border-brand-100 dark:border-brand-900/50 hover:bg-brand-50 dark:hover:bg-dark-700'}`}
        >
          <Download size={18} /> {activeTool === 'quote' ? 'Teklifleri Kapat' : 'Teklifleri Gör'}
        </button>

        <div className="grid grid-cols-2 gap-3">
          <button 
            onClick={() => {
              const shapEl = document.getElementById('shap-chart-section');
              if (shapEl) shapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }}
            className="py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all bg-white dark:bg-dark-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-dark-700 hover:bg-slate-50 dark:hover:bg-dark-700"
          >
            <BarChartIcon size={16} /> Grafiğe Git
          </button>
          <div className="relative">
            <button 
              onClick={() => setDownloadDropdownOpen(!downloadDropdownOpen)}
              className="w-full py-2.5 bg-white dark:bg-dark-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-dark-700 rounded-xl font-medium text-sm hover:bg-slate-50 dark:hover:bg-dark-700 flex items-center justify-center gap-2 transition-all"
            >
              <Download size={16} /> İndir
            </button>
            {downloadDropdownOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setDownloadDropdownOpen(false)}></div>
                <div className="absolute top-full left-0 mt-2 w-56 bg-white dark:bg-dark-800 border border-slate-200 dark:border-dark-700 shadow-xl rounded-xl overflow-hidden z-20 divide-y divide-slate-100 dark:divide-dark-700">
                  <button 
                    onClick={() => downloadExecutivePDF()} 
                    disabled={downloadingPdf} 
                    className="w-full text-left px-4 py-2.5 text-xs text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-dark-700 flex items-center gap-2 font-bold transition-colors"
                  >
                    {downloadingPdf ? <Loader2 size={14} className="animate-spin text-brand-500" /> : <FileText size={14} className="text-brand-500" />}
                    Resmi Tahsis Raporu (PDF)
                  </button>
                  <div>
                    <button onClick={() => { downloadNativePDF(); setDownloadDropdownOpen(false); }} className="w-full text-left px-4 py-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-700 flex items-center gap-2"><FileText size={14} /> Ekranı Yazdır</button>
                    <button onClick={() => { downloadCSV(); setDownloadDropdownOpen(false); }} className="w-full text-left px-4 py-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-700 flex items-center gap-2"><FileText size={14} /> CSV Tablosu</button>
                    <button onClick={() => { downloadJSON(); setDownloadDropdownOpen(false); }} className="w-full text-left px-4 py-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-dark-700 flex items-center gap-2"><FileJson size={14} /> JSON Verisi</button>
                  </div>
                </div>
              </>
            )}
          </div>
          <button 
            onClick={() => {
              setActiveTool(activeTool === 'simulator' ? 'none' : 'simulator');
              if (activeTool !== 'simulator') {
                setTimeout(() => {
                  document.getElementById('simulator-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
              }
            }}
            className={`py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all ${activeTool === 'simulator' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300' : 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/40'}`}
          >
            <Settings2 size={16} /> Simülatör
          </button>
          <button 
            onClick={() => {
              setActiveTool(activeTool === 'fraud' ? 'none' : 'fraud');
              if (activeTool !== 'fraud') {
                setTimeout(() => {
                  document.getElementById('fraud-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
              }
            }}
            className={`py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all ${activeTool === 'fraud' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300' : 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border border-amber-100 dark:border-amber-900/30 hover:bg-amber-100 dark:hover:bg-amber-900/40'}`}
          >
            <ShieldAlert size={16} /> Fraud İst.
          </button>
        </div>
      </div>

      <ShapChart shapData={shapData} />

      {activeTool === 'fraud' && fraudRisk !== null && (
        <div id="fraud-section" className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-amber-200 dark:border-amber-900/50 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
          <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <ShieldAlert className="text-amber-500" size={16} /> Fraud (Sahtekarlık) İstatistikleri
          </h3>
          <div className="flex items-center gap-4 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-xl">
            <div className="w-16 h-16 relative flex items-center justify-center flex-shrink-0">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-amber-200 dark:text-amber-900/50" strokeWidth="4" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className={`${fraudRisk > 10 ? 'text-red-500' : 'text-amber-500'}`} strokeDasharray={`${fraudRisk}, 100`} strokeWidth="4" stroke="currentColor" fill="none" strokeLinecap="round" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div className="absolute flex flex-col items-center justify-center">
                <span className={`text-sm font-black ${fraudRisk > 10 ? 'text-red-600' : 'text-amber-600'}`}>%{fraudRisk}</span>
              </div>
            </div>
            <div className="flex-1">
              <h4 className="font-bold text-amber-800 dark:text-amber-400 text-sm mb-2">Genel Risk Durumu</h4>
              <p className="text-xs text-amber-700/90 dark:text-amber-500/90 leading-relaxed mb-3">
                {fraudRisk > 10 
                  ? "Sistem bu profilde bazı anormallikler tespit etti. Başvurunun manuel olarak (uzman tarafından) incelenmesi önerilir. Özgeçmişteki tutarsızlıklar veya yüksek riskli kredi amacı bu duruma neden olmuş olabilir." 
                  : "Sistemdeki diğer onaylı profillerle uyumlu. Sentetik verilerde olağandışı bir örüntü tespit edilmedi."}
              </p>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 text-[11px] text-amber-800 dark:text-amber-400">
                  <CheckCircle2 size={12} className="text-emerald-500" /> Profil Tutarlılık Kontrolü
                </div>
                <div className="flex items-center gap-2 text-[11px] text-amber-800 dark:text-amber-400">
                  <CheckCircle2 size={12} className="text-emerald-500" /> Kara Liste (Default) Taraması
                </div>
                <div className="flex items-center gap-2 text-[11px] text-amber-800 dark:text-amber-400">
                  {fraudRisk > 10 ? <AlertCircle size={12} className="text-amber-500" /> : <CheckCircle2 size={12} className="text-emerald-500" />} DTI & Gelir Anomalisi
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTool === 'simulator' && <ScenarioSimulator result={result} />}

      {activeTool === 'quote' && (
        <div id="quote-section" className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-brand-200 dark:border-brand-900/50 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4 pb-3 border-b border-slate-100 dark:border-dark-700">
            <div>
              <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Building2 className="text-brand-500" size={18} /> Gerçek Banka Kredi Teklifleri
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Kredi risk değerlendirmenize ve talep ettiğiniz tutara göre karşılaştırmalı teklifler.
              </p>
            </div>

            {/* Vade Seçici */}
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-dark-900 p-1 rounded-xl">
              {[12, 24, 36].map((term) => (
                <button
                  key={term}
                  onClick={() => handleTermChange(term)}
                  className={`px-3 py-1 text-xs font-bold rounded-lg transition ${
                    selectedTerm === term 
                      ? 'bg-brand-600 text-white shadow-sm' 
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {term} Ay
                </button>
              ))}
            </div>
          </div>
          
          {offersLoading ? (
            <div className="flex flex-col justify-center items-center h-48 text-brand-500 gap-2">
              <Loader2 className="animate-spin" size={28} />
              <span className="text-xs font-medium text-slate-500">Bankalardan güncel faiz oranları hesaplanıyor...</span>
            </div>
          ) : offersError ? (
            <div className="p-4 bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400 text-xs rounded-xl border border-red-200 dark:border-red-800">
              {offersError}
            </div>
          ) : offers.length > 0 ? (
            <div className="space-y-4">
              {offers.map((offer, idx) => (
                <div 
                  key={idx} 
                  className="bg-slate-50 dark:bg-dark-900 p-4 rounded-2xl border border-slate-200 dark:border-dark-700 hover:border-brand-300 dark:hover:border-brand-700 transition-all hover:shadow-md"
                >
                  <div className="flex justify-between items-start mb-3 pb-2 border-b border-slate-200/70 dark:border-dark-700">
                    <div className="flex items-center gap-2.5">
                      <div 
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs shadow-sm"
                        style={{ backgroundColor: offer.color || '#3b82f6' }}
                      >
                        {offer.bank_name[0]}
                      </div>
                      <div>
                        <div className="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
                          {offer.bank_name}
                          {offer.badge && (
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                              offer.badge_type === 'success' 
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                : offer.badge_type === 'warning'
                                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                            }`}>
                              {offer.badge}
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400">{offer.product_name}</span>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-slate-400 block">Aylık Faiz</span>
                      <span className="font-black text-brand-600 dark:text-brand-400 text-sm">
                        %{offer.monthly_interest_rate.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 py-1 text-xs">
                    <div>
                      <span className="text-slate-400 block">Aylık Taksit:</span>
                      <span className="font-black text-emerald-600 dark:text-emerald-400 text-base">
                        ₺{offer.monthly_installment.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Toplam Geri Ödeme:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        ₺{offer.total_repayment.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Dosya Masrafı:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {offer.processing_fee > 0 ? `₺${offer.processing_fee.toLocaleString('tr-TR')}` : '0 TL (Masrafsız)'}
                      </span>
                    </div>
                  </div>

                  {offer.features && offer.features.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2.5 pt-2 border-t border-slate-100 dark:border-dark-800">
                      {offer.features.map((feat, fi) => (
                        <span key={fi} className="text-[10px] bg-slate-200/60 dark:bg-dark-800 text-slate-600 dark:text-slate-400 px-2 py-0.5 rounded-md font-medium">
                          ✓ {feat}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 pt-2 flex justify-between items-center">
                    <span className="text-[11px] text-slate-400">
                      Vade: <strong>{offer.term_months} Ay</strong> • YMO: %{offer.annual_cost_rate}
                    </span>
                    <a
                      href={offer.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl transition shadow-sm"
                    >
                      Hemen Başvur <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              ))}

              {offerDisclaimer && (
                <p className="text-[11px] text-slate-400 dark:text-slate-500 italic mt-3 text-center">
                  * {offerDisclaimer}
                </p>
              )}
            </div>
          ) : (
            <div className="text-center text-slate-500 text-sm py-8">Teklif bulunamadı.</div>
          )}
        </div>
      )}
    </div>
  );
}
