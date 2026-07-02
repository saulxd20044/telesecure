"use client";

export default function DashboardPage() {
  return (
    <>
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Panel de Control General</h1>
        <p className="text-gray-400 text-sm mt-1">Resumen del estado del call center en el turno actual</p>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
          <h3 className="text-gray-400 text-sm font-medium">Estado del Canal SIP</h3>
          <p className="text-3xl font-bold text-green-400 mt-2">Registrado</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
          <h3 className="text-gray-400 text-sm font-medium">Llamadas del Agente</h3>
          <p className="text-3xl font-bold text-white mt-2">24</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
          <h3 className="text-gray-400 text-sm font-medium">Precisión de IA (Análisis)</h3>
          <p className="text-3xl font-bold text-blue-400 mt-2">94.2%</p>
        </div>
      </main>
    </>
  );
}