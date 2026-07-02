"use client";

import { useEffect, useState } from "react";

export default function LiveMonitorPage() {
  const [calls, setCalls] = useState([]);
  const [status, setStatus] = useState("connecting"); // connecting, online, offline

  useEffect(() => {
    // 🚀 Detección dinámica de la IP para el WebSocket
    const hostIP = typeof window !== "undefined" ? window.location.hostname : "localhost";
    const BACKEND_PORT = 8000;
    
    // Conexión al endpoint de WebSockets de FastAPI
    const ws = new WebSocket(`ws://${hostIP}:${BACKEND_PORT}/api/ws/live`);

    ws.onopen = () => {
      setStatus("online");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Esperamos recibir un array de llamadas activas desde el backend
        if (Array.isArray(data)) {
          setCalls(data);
        }
      } catch (err) {
        console.error("Error al parsear evento de WebSocket:", err);
      }
    };

    ws.onclose = () => {
      setStatus("offline");
    };

    ws.onerror = () => {
      setStatus("offline");
    };

    // Limpieza al desmontar el módulo
    return () => {
      ws.close();
    };
  }, []);

  return (
    <>
      {/* Encabezado con estado de conexión */}
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Monitoreo en Tiempo Real</h1>
          <p className="text-gray-400 text-sm mt-1">Canales activos y llamadas concurrentes en Asterisk</p>
        </div>
        
        {/* Badge de Estado del WebSocket */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border bg-gray-800">
          <span className={`w-2 h-2 rounded-full ${
            status === "online" ? "bg-green-500 animate-pulse" : status === "connecting" ? "bg-yellow-500" : "bg-red-500"
          }`}></span>
          <span className={status === "online" ? "text-green-400" : status === "connecting" ? "text-yellow-400" : "text-red-400"}>
            {status === "online" ? "Servidor Conectado" : status === "connecting" ? "Conectando..." : "Servidor Desconectado"}
          </span>
        </div>
      </header>

      {/* Métrica rápida */}
      <div className="mb-8 bg-gray-800/50 border border-gray-700 p-4 rounded-xl flex items-center justify-between max-w-xs">
        <span className="text-gray-400 text-sm">Llamadas Concurrentes:</span>
        <span className="text-2xl font-bold text-blue-400">{calls.length}</span>
      </div>

      {/* Tabla / Grid de llamadas activas */}
      {calls.length === 0 ? (
        <div className="flex flex-col items-center justify-center border border-dashed border-gray-700 rounded-2xl p-16 text-center bg-gray-800/20">
          <svg className="w-12 h-12 text-gray-650 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-300">No hay llamadas activas</h3>
          <p className="text-gray-500 text-sm max-w-sm mt-1">En cuanto una extensión de Asterisk marque o reciba tráfico, aparecerá reflejada aquí automáticamente.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-700 bg-gray-800">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-850 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                <th className="px-6 py-4">Extensión / Canal</th>
                <th className="px-6 py-4">Número Destino</th>
                <th className="px-6 py-4">Estado</th>
                <th className="px-6 py-4">Duración</th>
                <th className="px-6 py-4">Análisis de IA</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700 text-sm text-gray-300">
              {calls.map((call) => (
                <tr key={call.id} className="hover:bg-gray-750 transition-colors">
                  <td className="px-6 py-4 font-medium text-white flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                      📞
                    </div>
                    <div>
                      <div>Ext. {call.extension}</div>
                      <span className="text-xs text-gray-500">{call.channel}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-mono text-gray-200">{call.destination}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      call.status === "Up" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                    }`}>
                      {call.status === "Up" ? "Hablando" : "Timbrando"}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-sm text-gray-400">{call.duration}s</td>
                  <td className="px-6 py-4">
                    <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2.5 py-1 rounded-md font-medium">
                      {call.ai_status || "Procesando..."}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}