# Fase 4 — Auditoría de inicios de sesión en midPoint
## Controles ISO 27001: A.8.15 (Registro de eventos) y A.8.16 (Monitoreo de actividades)

Fecha de extracción: 18/06/2026
Fuente: tabla `ma_audit_event` del repositorio PostgreSQL de midPoint (auditoría nativa)
Evidencia archivada: `evidencia/04_midpoint_logins.txt`

## Consulta ejecutada (extracción directa de la BD)
```sql
SELECT timestamp AS fecha, initiatorname AS usuario, outcome AS resultado,
       channel AS canal, COALESCE(remotehostaddress,'N/A') AS ip_origen
FROM ma_audit_event
WHERE eventtype = 'CREATE_SESSION'
ORDER BY timestamp DESC;
```

## Resultados

| # | Fecha/hora | Usuario | Resultado | Canal | IP origen |
|---|---|---|---|---|---|
| 1 | 2026-06-17 22:23:52 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 2 | 2026-06-16 22:55:54 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 3 | 2026-06-16 22:29:27 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 4 | 2026-06-16 21:39:27 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 5 | 2026-06-16 20:47:02 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 6 | 2026-06-16 20:10:36 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 7 | 2026-06-16 17:31:13 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 8 | 2026-06-16 16:59:13 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |
| 9 | 2026-06-16 16:42:22 | administrator | SUCCESS | GUI (#user) | 172.21.0.1 |

## Resumen de seguridad (A.8.16 — detección de anomalías)

| Resultado | Cantidad |
|---|---|
| SUCCESS | 9 |
| Fallidos (FATAL_ERROR) | 0 |

## Análisis de auditor

1. **Trazabilidad completa (A.8.15):** cada sesión queda registrada automáticamente
   con marca temporal, identidad del iniciador, canal de acceso e IP de origen.
   No requiere configuración adicional: la auditoría es nativa del repositorio.

2. **No repudio:** los registros viven en la tabla `ma_audit_event` de PostgreSQL,
   fuera del alcance del usuario final y protegidos por la segregación de cuentas
   de BD definida en la Fase 2. El `sessionidentifier` permite correlacionar cada
   sesión con las acciones posteriores (ADD_OBJECT, MODIFY_OBJECT).

3. **Monitoreo (A.8.16):** 0 intentos fallidos en el periodo auditado → sin indicios
   de ataque de fuerza bruta. En producción, un pico de FATAL_ERROR en CREATE_SESSION
   sería el indicador temprano de un ataque de credenciales.

4. **Observación de hardening:** todos los accesos provienen de `172.21.0.1` (gateway
   de la red Docker) vía un único usuario `administrator`. Recomendación documentada:
   en producción, crear cuentas nominales por operador (no compartir `administrator`)
   y restringir el origen de las sesiones administrativas — refuerza A.8.2
   (derechos de acceso privilegiado) y la atribución individual.

## Conclusión para el informe
La auditoría evidencia que TeleSecure cumple A.8.15 y A.8.16: el sistema IAM registra
y permite monitorear todos los inicios de sesión, con datos suficientes para
investigación forense (quién, cuándo, desde dónde, con qué resultado) y para
detección temprana de accesos no autorizados.
