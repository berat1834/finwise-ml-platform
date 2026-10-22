import React, { useState, useRef, useEffect } from 'react';
import { Bot, User, BrainCircuit, Send, Eraser, X } from 'lucide-react';
import { fetchApi } from '@/lib/api';

export default function AiChatWidget({ result, formData }: { result: any, formData: any }) {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState<{role: 'user' | 'assistant', text: string}[]>([]);
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (result && result.decision) {
      setChatHistory([{
        role: 'assistant', 
        text: `Merhaba! Başvurunuz incelendi ve **${result.decision === 'Approved' ? 'ONAYLANDI' : 'REDDEDİLDİ'}**. Model kararı hakkında ne bilmek istersiniz?`
      }]);
      
      // Highlight chat bot playfully
      setTimeout(() => {
        const chatBtn = document.getElementById('chat-toggle-btn');
        if(chatBtn && !isChatOpen) {
          chatBtn.classList.add('animate-bounce');
          setTimeout(() => chatBtn.classList.remove('animate-bounce'), 3000);
        }
      }, 1000);
    } else {
      setChatHistory([]);
    }
  }, [result]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, isChatOpen]);

  const sendChatMessage = async () => {
    if(!chatInput.trim()) return;
    const newChat = [...chatHistory, {role: 'user' as const, text: chatInput}];
    setChatHistory(newChat);
    setChatInput("");
    
    try {
      const data = await fetchApi('/api/v2/ai-risk-assistant', {
        method: 'POST',
        body: JSON.stringify({
          question: chatInput,
          model_prediction: result ? (1 - result.onay_olasiligi) : 0.5,
          customer_data: {
            annual_income: formData.person_income ? parseFloat(formData.person_income) : 0,
            requested_amount: formData.loan_amnt ? parseFloat(formData.loan_amnt) : 0,
          },
          fairness_context: {}
        })
      });

      setChatHistory([...newChat, {
        role: 'assistant', 
        text: data.answer || "Üzgünüm, şu an yanıt veremiyorum."
      }]);
    } catch (err) {
      setChatHistory([...newChat, {
        role: 'assistant', 
        text: "Bağlantı hatası oluştu, lütfen daha sonra tekrar deneyin."
      }]);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 print:hidden flex flex-col items-end">
      {isChatOpen && (
        <div className="mb-4 w-[340px] bg-white dark:bg-dark-800 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 duration-300">
          <div className="bg-slate-50 dark:bg-dark-900 border-b border-slate-200 dark:border-dark-700 p-3 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-brand-600" />
              <h3 className="font-bold text-sm text-slate-700 dark:text-slate-300">FinWise AI Asistanı</h3>
            </div>
            <div className="flex gap-1">
              <button onClick={() => setChatHistory([])} className="text-[10px] bg-slate-200 dark:bg-dark-700 hover:bg-slate-300 dark:hover:bg-dark-600 px-2 py-1 rounded text-slate-600 dark:text-slate-400 transition" title="Geçmişi Temizle">
                <Eraser size={12} />
              </button>
              <button onClick={() => setIsChatOpen(false)} className="p-1 hover:bg-slate-200 dark:hover:bg-dark-700 rounded text-slate-500 transition">
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="h-[300px] p-4 overflow-y-auto space-y-4 custom-scrollbar bg-white dark:bg-dark-800">
            {chatHistory.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400">
                <BrainCircuit size={48} className="opacity-20 mb-3" />
                <p className="text-xs text-center px-4">
                  {result ? "Analiz tamamlandı. Kararla ilgili sorularınızı sorabilirsiniz." : "Merhaba! FinWise platformu ve başvuru süreci hakkında bana sorular sorabilirsiniz."}
                </p>
              </div>
            ) : (
              chatHistory.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-slate-200 dark:bg-dark-700 text-slate-600 dark:text-slate-300' : 'bg-brand-600 text-white shadow-glow'}`}>
                    {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                  </div>
                  <div className={`p-2.5 rounded-xl text-[12px] max-w-[85%] ${msg.role === 'user' ? 'bg-slate-800 dark:bg-slate-700 text-white rounded-tr-none' : 'bg-slate-50 dark:bg-dark-900 border border-slate-100 dark:border-dark-700 text-slate-700 dark:text-slate-300 rounded-tl-none shadow-sm'}`}>
                    {msg.text}
                  </div>
                </div>
              ))
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="p-3 bg-slate-50 dark:bg-dark-900 border-t border-slate-200 dark:border-dark-700">
            <div className="relative">
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendChatMessage()}
                placeholder={result ? "Bu karar neden verildi?" : "Nasıl kredi başvurusu yaparım?"}
                className="w-full pl-3 pr-9 py-2 bg-white dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-lg text-xs focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none dark:text-white transition"
              />
              <button 
                onClick={sendChatMessage}
                disabled={!chatInput.trim()}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 w-6 h-6 bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 dark:disabled:bg-dark-700 text-white rounded-[4px] flex items-center justify-center transition"
              >
                <Send size={12} />
              </button>
            </div>
          </div>
        </div>
      )}
      <button 
        id="chat-toggle-btn"
        onClick={() => setIsChatOpen(!isChatOpen)}
        className={`w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all duration-300 ${isChatOpen ? 'bg-slate-800 dark:bg-slate-700 hover:bg-slate-900' : 'bg-brand-600 hover:bg-brand-700 shadow-glow'}`}
      >
        {isChatOpen ? <X size={24} className="text-white" /> : <Bot size={28} className="text-white" />}
      </button>
    </div>
  );
}
