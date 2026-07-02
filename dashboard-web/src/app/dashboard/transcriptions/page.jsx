'use client';

import { useState, useEffect } from 'react';
import api from "@/lib/api"; // Ajusta la ruta a tu instancia de Axios

export default function TranscriptionsPage() {
  const [transcriptions, setTranscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // URL de tu contenedor de la API de Python (ajústala a tu puerto real, ej: 8000)
  const fetchTranscriptions = async () => {
    try {
      setLoading(true);
        const res = await api.get("/transcriptions");
        if (res.status !== 200) throw new Error('Error al conectar con la API de la IA');
        console.log(res.data);
      setTranscriptions(res.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTranscriptions();
    // Opcional: Auto-refrescar cada 10 segundos para ver llamadas en tiempo real
    const interval = setInterval(fetchTranscriptions, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && transcriptions.length === 0) {
    return <div className="p-8 text-center text-gray-500 animate-pulse">Cargando transcripciones de llamadas...</div>;
  }

  if (error) {
    return <div className="p-4 mx-8 my-4 text-red-700 bg-red-100 rounded-lg">⚠️ Error: {error}</div>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
            <span className="opacity-90">🎙️</span> Historial de Llamadas Transcritas
        </h1>
        <button 
          onClick={fetchTranscriptions}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
        >
          🔄 Actualizar
        </button>
      </div>

      {transcriptions.length === 0 ? (
        <div className="p-12 text-center text-gray-400 border-2 border-dashed rounded-xl">
          No hay llamadas transcritas registradas aún.
        </div>
      ) : (
        <div className="space-y-4">
        {transcriptions.map((item) => (
            <div 
            key={item.uniqueid} 
            className="p-5 bg-slate-900/50 text-slate-100 border border-slate-800 rounded-xl hover:border-slate-700 hover:shadow-lg hover:shadow-black/20 transition-all"
            >
            {/* Metadatos (ID y Fecha) */}
            <div className="flex justify-between items-center mb-4 text-xs text-slate-400">
                <span className="font-mono bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-700">
                ID: {item.uniqueid}
                </span>
                <span className="flex items-center gap-1 text-slate-400">
                📅 {new Date(item.calldate).toLocaleString()}
                </span>
            </div>

            {/* Bloque de la Transcripción */}
            <div className="bg-slate-950/60 p-4 rounded-lg border-l-4 border-blue-500 shadow-inner">
                <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line font-medium">
                {item.transcription}
                </p>
            </div>
            </div>
        ))}
        </div>
      )}
    </div>
  );
}