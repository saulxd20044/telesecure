"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({ children }) {
  const [authorized, setAuthorized] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
    } else {
      setAuthorized(true);
    }
  }, [router]);

  if (!authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900 text-white">
        Verificando sesión...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex">
      {/* Menú de navegación lateral fijo */}
      <Sidebar />

      {/* Espacio para los contenidos de los módulos (Desplazado a la derecha por el menú de 64 de ancho) */}
      <div className="flex-1 ml-64 p-8 min-h-screen overflow-y-auto">
        {children}
      </div>
    </div>
  );
}