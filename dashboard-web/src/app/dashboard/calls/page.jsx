"use client";
import { useState, useEffect } from "react";
import api from "@/lib/api"; // Ajusta la ruta a tu instancia de Axios

const ITEMS_PER_PAGE = 20;

export default function CDRHistory() {
  const [cdrData, setCdrData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filtros
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [extension, setExtension] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const fetchCDR = async (resetOffset = false) => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        extension: extension || undefined,
        limit: ITEMS_PER_PAGE,
        offset: resetOffset ? 0 : offset,
      };

      const response = await api.get("/cdr", { params });
      const data = response.data;

      if (data.error) {
        setError(data.error);
        setCdrData([]);
        setTotal(0);
      } else {
        setCdrData(data.cdr);
        setTotal(data.total);
        if (resetOffset) setOffset(0);
      }
    } catch (err) {
      console.error("Error al obtener CDR:", err);
      setError("No se pudo cargar el historial.");
      setCdrData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  // Cargar automáticamente al montar y cuando cambien los filtros
  useEffect(() => {
    fetchCDR(true); // resetea el offset al cambiar filtros
  }, [startDate, endDate, extension]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchCDR(true);
  };

  const nextPage = () => setOffset((prev) => prev + ITEMS_PER_PAGE);
  const prevPage = () => setOffset((prev) => Math.max(prev - ITEMS_PER_PAGE, 0));

  return (
    <>
      {/* Encabezado */}
      <header className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Historial de Llamadas</h1>
          <p className="text-gray-400 text-sm mt-1">
            Registros CDR de Asterisk / FreePBX
          </p>
        </div>
      </header>

      {/* Filtros */}
      <form onSubmit={handleSearch} className="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Fecha inicio</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Fecha fin</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Extensión</label>
          <input
            type="text"
            placeholder="Ej. 101"
            value={extension}
            onChange={(e) => setExtension(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </form>

      {/* Botón de búsqueda */}
      <div className="flex justify-end mb-6">
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? "Cargando..." : "Buscar"}
        </button>
      </div>

      {/* Contenido */}
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {cdrData.length === 0 && !loading && !error ? (
        <div className="flex flex-col items-center justify-center border border-dashed border-gray-700 rounded-2xl p-16 text-center bg-gray-800/20">
          <svg className="w-12 h-12 text-gray-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-300">Sin registros</h3>
          <p className="text-gray-500 text-sm max-w-sm mt-1">
            No se encontraron llamadas con los filtros actuales.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-700 bg-gray-800">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-850 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                <th className="px-6 py-4">Fecha</th>
                <th className="px-6 py-4">Origen</th>
                <th className="px-6 py-4">Destino</th>
                <th className="px-6 py-4">Duración</th>
                <th className="px-6 py-4">Facturación</th>
                <th className="px-6 py-4">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700 text-sm text-gray-300">
              {cdrData.map((record) => (
                <tr key={record.uniqueid} className="hover:bg-gray-750 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs">
                    {new Date(record.calldate).toLocaleString("es-PE")}
                  </td>
                  <td className="px-6 py-4 font-medium">{record.src}</td>
                  <td className="px-6 py-4">{record.dst}</td>
                  <td className="px-6 py-4">{record.duration}s</td>
                  <td className="px-6 py-4">{record.billsec}s</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        record.disposition === "ANSWERED"
                          ? "bg-green-500/10 text-green-400 border border-green-500/20"
                          : record.disposition === "NO ANSWER"
                          ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      {record.disposition}
                    </span>
                  </td>
                  
                </tr>
              ))}
            </tbody>
          </table>

          {/* Paginación */}
          <div className="flex justify-between items-center px-6 py-3 border-t border-gray-700 bg-gray-800/50">
            <span className="text-xs text-gray-400">
              Mostrando {cdrData.length} de {total} registros
            </span>
            <div className="flex gap-2">
              <button
                onClick={prevPage}
                disabled={offset === 0 || loading}
                className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded-lg transition"
              >
                Anterior
              </button>
              <button
                onClick={nextPage}
                disabled={cdrData.length < ITEMS_PER_PAGE || loading}
                className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded-lg transition"
              >
                Siguiente
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}