import React from 'react';
import { BarChartIcon } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { ShapFeature } from '@/types';

export default function ShapChart({ shapData }: { shapData: ShapFeature[] }) {
  if (!shapData || shapData.length === 0) return null;

  return (
    <div id="shap-chart-section" className="bg-white dark:bg-dark-800 p-5 rounded-2xl border border-slate-200 dark:border-dark-700 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300 flex flex-col">
      <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-2 flex items-center gap-2">
        <BarChartIcon className="text-brand-500" size={16} /> 📊 SHAP Özellik Önem Grafiği
      </h3>
      
      <div className="min-h-[200px] w-full pt-4">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={shapData} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
            <XAxis type="number" hide />
            <YAxis dataKey="feature" type="category" width={150} tick={{fill: '#888', fontSize: 11}} axisLine={false} tickLine={false} />
            <RechartsTooltip cursor={{fill: 'transparent'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }} />
            <ReferenceLine x={0} stroke="#cbd5e1" strokeDasharray="3 3" />
            <Bar dataKey="impact" radius={[0, 4, 4, 0]} barSize={12}>
              {shapData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={(entry.impact ?? 0) < 0 ? '#10b981' : '#ef4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
