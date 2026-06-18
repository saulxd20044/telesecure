# FASE 4 — Resumen ejecutivo de auditoría de seguridad y calidad
## Proyecto TeleSecure · ISO/IEC 27001:2022 + ISO/IEC 25010

| # | Actividad | Control / Norma | Herramienta | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1 | Escaneo de vulnerabilidades de imágenes | A.8.8 | Trivy | 970 hallazgos; 84% en FreePBX; webhook propio el más limpio (11) | 02_trivy_*.txt |
| 2 | Auditoría de inicios de sesión | A.8.15 / A.8.16 | PostgreSQL (ma_audit_event) | 9 logins, 0 fallidos; trazabilidad completa | 04_midpoint_logins.txt |
| 3 | Calidad de código del conector | ISO 25010 | SonarQube | Fiabilidad A, Mantenibilidad A; 4 hotspots revisados | (dashboard) |
| 4 | Cifrado de telefonía | A.8.24 | FreePBX/Asterisk | TLS 1.2 + SRTP obligatorio forzado por extensión | 01_tls_*.txt |

## Hallazgos principales y tratamiento
1. **FreePBX concentra el 84% de las vulnerabilidades** (imagen "todo en uno"):
   tratamiento por aislamiento de red, no por parcheo. Riesgo residual aceptado.
2. **El componente desarrollado a medida (webhook) es el más seguro:** 11 CVEs
   (vs 869 de FreePBX), rating A en Fiabilidad y Mantenibilidad. Valida el diseño
   minimalista (menor superficie de ataque).
3. **Cifrado forzado, no opcional:** TLS+SRTP obligatorio a nivel de extensión.
4. **Trazabilidad y no repudio:** auditoría nativa de midPoint registra cada sesión
   con timestamp, usuario, IP y resultado, fuera del alcance del usuario final.

## Postura general de seguridad
El sistema demuestra defensa en profundidad: cifrado en el perímetro (TLS/SRTP),
gestión de identidades con auditoría (midPoint), segmentación de red (Docker),
componente propio minimalista, y proceso activo de gestión de vulnerabilidades.
Los hallazgos se priorizaron por riesgo y se les asignó tratamiento, demostrando
madurez del proceso de aseguramiento (no la ausencia irreal de hallazgos).
