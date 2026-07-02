import axios from "axios";

// 1. Obtener la IP dinámicamente en el cliente, o usar localhost si es Server-Side Rendering
const hostIP = typeof window !== "undefined" ? window.location.hostname : "localhost";
const BACKEND_PORT = 8000; // Puedes cambiarlo si usas otro puerto en tu .env

// Instancia personalizada de Axios
const api = axios.create({
  baseURL: `http://${hostIP}:${BACKEND_PORT}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// 2. INTERCEPTOR: Añade automáticamente el token JWT a todas las peticiones
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) {
        // Inyecta el token en la cabecera para los módulos que requieran autenticación en FastAPI
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
