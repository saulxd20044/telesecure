# Fase 4 — Resultados del escaneo Trivy (A.8.8 Gestión de vulnerabilidades técnicas)

Fecha: 18/06/2026 · Herramienta: Trivy (aquasec/trivy) · Severidad: CRITICAL + HIGH

## Tabla consolidada de hallazgos

| Imagen | Componente | SO base | CRITICAL | HIGH | Total | Origen |
|---|---|---|---|---|---|---|
| blacksunsolutions/freepbx:latest | PBX (FreePBX 17) | Debian 12 | 128 + 1 = 129 | 737 + 3 = 740 | 869 | SO + libs |
| evolveum/midpoint:latest-alpine | IAM (midPoint) | Alpine 3.23 | 2 + 13 = 15 | 20 + 20 = 40 | 55 | SO + Java/jar |
| postgres:16-alpine | BD de midPoint | Alpine 3.23 | 0 + 1 = 1 | 3 + 14 = 17 | 18 | SO + libs |
| mariadb:10.6 | BD de FreePBX | (Debian) | 0 + 1 = 1 | 2 + 14 = 16 | 17 | SO + libs |
| telesecure-webhook:latest | Conector propio | Debian 13 | 2 | 9 | 11 | SO + Python |

## Análisis de auditor

1. **FreePBX concentra el 84% de las vulnerabilidades (869 de ~1030).**
   Causa raíz: es una imagen "todo en uno" (Debian completo + Asterisk + Apache +
   PHP + módulos), con 1266 paquetes del sistema. Mayor superficie = más CVEs.
   Esto es típico de appliances de telefonía y constituye el hallazgo principal.

2. **El componente desarrollado a medida (webhook) es el más limpio: solo 11.**
   Construido sobre python-slim con dependencias mínimas (49.8 MB vs 1.17 GB de
   FreePBX). Demuestra que el diseño minimalista reduce la superficie de ataque
   (principio de menor funcionalidad, ISO 27001 A.8.9 / defensa en profundidad).

3. **Las bases de datos (PostgreSQL y MariaDB) están razonablemente contenidas**
   (~17-18 c/u), al usar variantes Alpine/slim. Riesgo mitigable con actualización
   de tag.

## Plan de tratamiento (por imagen)

| Imagen | Tratamiento recomendado | Justificación |
|---|---|---|
| FreePBX | **Mitigar por aislamiento** (no actualizable a corto plazo): segmentación de red, firewall, exponer solo puertos SIP/GUI necesarios, no exponer a Internet. Aceptar riesgo residual documentado. | La imagen depende del upstream; recompilar está fuera de alcance académico. |
| midPoint | **Actualizar** a la última etiqueta estable de Evolveum cuando publiquen parche; vigilar los 15 CRITICAL de librerías Java. | Mantenible vía cambio de tag. |
| PostgreSQL / MariaDB | **Actualizar** a la última minor (16.x / 10.6.x) en el próximo ciclo. | Bajo esfuerzo, alto retorno. |
| webhook (propio) | **Corregir**: actualizar las dependencias Python con CVE (los 2 CRITICAL) y rebase de la imagen base Debian 13. | Es código/imagen bajo nuestro control directo. |

## Conclusión para el informe
El escaneo evidencia gestión activa de vulnerabilidades (A.8.8). El hallazgo clave
no es "cero CVEs" (irreal en un appliance como FreePBX) sino la **priorización por
riesgo y control**: el componente propio es el más seguro, y el de mayor riesgo
(FreePBX) se trata por aislamiento de red, no por parcheo imposible.
