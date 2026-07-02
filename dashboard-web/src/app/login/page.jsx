"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api"; // <--- Importas tu cliente centralizado

export default function LoginPage() {
  const [extension, setExtension] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) router.push("/dashboard");
  }, [router]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // 🚀 Súper limpio: Ya no configuras URLs aquí, solo usas la ruta relativa del endpoint
      const response = await api.post("/auth/login", {
        extension,
        secret,
      });

      const data = response.data;
      localStorage.setItem("token", data.token);
      localStorage.setItem("extension", data.extension);

      router.push("/dashboard");
    } catch (err) {
      if (err.response && err.response.data) {
        setError(err.response.data.detail || "Error en la autenticación");
      } else {
        setError("No se pudo conectar con el servidor de Asterisk");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-900 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 bg-gray-800 p-8 rounded-xl shadow-lg border border-gray-700">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">TeleSecure Portal</h2>
          <p className="mt-2 text-center text-sm text-gray-400">Ingresa usando tu extensión de FreePBX</p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-500 text-sm p-3 rounded-lg text-center">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Número de Extensión</label>
              <input
                type="text"
                required
                value={extension}
                onChange={(e) => setExtension(e.target.value)}
                className="relative block w-full rounded-lg border-0 bg-gray-700 py-2.5 text-white placeholder-gray-400 ring-1 ring-inset ring-gray-650 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm px-3"
                placeholder="Ej. 101"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Contraseña SIP (Secret)</label>
              <input
                type="password"
                required
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                className="relative block w-full rounded-lg border-0 bg-gray-700 py-2.5 text-white placeholder-gray-400 ring-1 ring-inset ring-gray-650 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm px-3"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center rounded-lg bg-blue-600 px-3 py-3 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors disabled:opacity-50"
            >
              {loading ? "Verificando..." : "Iniciar Sesión"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
