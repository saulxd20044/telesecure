'use client';

import { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import api from "@/lib/api"; // Ajusta la ruta a tu instancia de Axios

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = async () => {
    try {
      const res = await api.get('/metrics');
      setData(res.data);
    } catch (err) {
      console.error("Error cargando métricas", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000); // Actualiza cada 30 segundos
    return () => clearInterval(interval);
  }, []);

  if (loading || !data) return <div className="text-center p-12 text-slate-400 animate-pulse">Analizando métricas del Call Center...</div>;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-100">📊 Panel de Analítica Avanzada</h1>
        <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full animate-pulse flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span> En Vivo
        </span>
      </div>

      {/* TARJETAS DE MÉTRICAS (KPINs) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        
        {/* Extensiones */}
        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Extensiones Activas</p>
          <p className="text-3xl font-extrabold mt-2 text-blue-400">
            {data.connected_extensions} <span className="text-sm font-normal text-slate-500">/ {data.total_extensions}</span>
          </p>
        </div>

        {/* Total Llamadas */}
        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Llamadas (7D)</p>
          <p className="text-3xl font-extrabold mt-2 text-purple-400">{data.total_calls}</p>
        </div>

        {/* Tasa de Éxito */}
        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Tasa de Efectividad</p>
          <p className="text-3xl font-extrabold mt-2 text-emerald-400">
            {data.total_calls > 0 ? ((data.answered_calls / data.total_calls) * 100).toFixed(1) : 0}%
          </p>
        </div>

        {/* Promedio de Conversación */}
        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Duración Promedio</p>
          <p className="text-3xl font-extrabold mt-2 text-amber-400">
            {Math.floor(data.avg_duration_seconds / 60)}m {Math.floor(data.avg_duration_seconds % 60)}s
          </p>
        </div>
      </div>

      {/* GRÁFICO DE RENDIMIENTO */}
      <div className="p-5 bg-slate-900/50 border border-slate-800 rounded-xl">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-200">📈 Tráfico Histórico de Llamadas</h2>
          <p className="text-xs text-slate-500">Volumen total vs llamadas contestadas con éxito</p>
        </div>

        <div className="w-full h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.calls_chart_data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="fecha" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }}
                itemStyle={{ color: '#3b82f6' }}
              />
              <Area type="monotone" dataKey="cantidad" name="Total llamadas" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorCalls)" />
              <Area type="monotone" dataKey="contestadas" name="Contestadas" stroke="#10b981" strokeWidth={1.5} fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}