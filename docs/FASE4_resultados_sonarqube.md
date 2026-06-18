# Fase 4 — Análisis de calidad de código con SonarQube
## Característica ISO/IEC 25010: Mantenibilidad, Fiabilidad y Seguridad

Fecha: 18/06/2026 · Herramienta: SonarQube Community 26.6 (efímero en Docker)
Componente analizado: `webhook/webhook_provisioner.py` (conector de aprovisionamiento, Fase 3)
Líneas de código: 321

## Dashboard de resultados

| Dimensión | Métrica | Rating | ISO 25010 |
|---|---|---|---|
| **Reliability** | 0 bugs | **A** | Fiabilidad (madurez) — sin defectos |
| **Maintainability** | 0 code smells | **A** | Mantenibilidad — código limpio |
| **Security** | 1 issue + 3 hotspots | E | Seguridad — requiere revisión (ver abajo) |
| **Duplications** | 0.0% sobre 494 líneas | ✔ | Mantenibilidad — sin duplicación |
| **Coverage** | 0.0% (no medido) | — | Tests unitarios existen (32), cobertura no instrumentada |

## Análisis de los 3 Security Hotspots (revisión de auditor)

### 1. CSRF — Prioridad Alta — `app = Flask(__name__)`
- **Hallazgo:** Flask sin protección CSRF explícita.
- **Evaluación:** El webhook es una **API máquina-a-máquina** autenticada por token
  (`X-Auth-Token`), no una aplicación web con sesiones de navegador ni cookies.
  El ataque CSRF requiere una sesión de navegador autenticada por cookie, que aquí
  no existe.
- **Decisión:** **SAFE** (riesgo no aplicable al patrón de integración). Documentado.

### 2. Permission — Prioridad Media — `host='0.0.0.0'`
- **Hallazgo:** El servicio escucha en todas las interfaces.
- **Evaluación:** Necesario para que el contenedor acepte conexiones de midPoint
  dentro de la red Docker. **Mitigado** porque el contenedor vive en una red Docker
  privada y segmentada (Fase 2); el puerto no se publica al host salvo lo necesario.
- **Decisión:** **ACKNOWLEDGED** con mitigación por segmentación de red.

### 3. Encryption of Sensitive Data — Prioridad Baja
- **Hallazgo:** Manejo de datos sensibles / transporte sin cifrar.
- **Evaluación:** Las llamadas internas (midPoint→webhook→FreePBX) viajan por la red
  Docker privada. El cifrado del perímetro externo (TLS/SRTP de las extensiones SIP)
  se trata en el ítem 1 de la Fase 4. El token de autenticación se inyecta por
  variable de entorno (no hardcodeado en el repositorio).
- **Decisión:** **ACKNOWLEDGED**; tratamiento de cifrado en perímetro documentado.

## Conclusión para el informe
El componente desarrollado a medida obtiene **rating A en Fiabilidad y Mantenibilidad**
(0 bugs, 0 code smells, 0% duplicación) sobre 321 líneas — evidencia de código limpio
y mantenible (ISO 25010). Los hotspots de seguridad fueron **revisados individualmente**
y clasificados con justificación técnica: ninguno representa una vulnerabilidad
explotable en el contexto de despliegue (API M2M autenticada por token en red Docker
segmentada). Esta revisión razonada —no el "cero hallazgos"— es la evidencia de
madurez del proceso de aseguramiento de calidad.

> Nota metodológica: SonarQube se ejecutó de forma efímera (contenedor temporal),
> sin dejar residuos en la infraestructura, alineado con el principio de mínima
> persistencia de herramientas de auditoría.

## Issue de Seguridad (1) — análisis detallado

**"Avoid binding the application to all network interfaces"**
- Severidad: Blocker · Línea L479 · Tags: `least-privilege`, `fastapi`
- **Hallazgo:** El servicio Flask hace `app.run(host='0.0.0.0', ...)`, escuchando en
  todas las interfaces de red.
- **Evaluación de auditor:** En un despliegue **contenedorizado**, escuchar en
  `0.0.0.0` es necesario y es práctica estándar: el contenedor no conoce a priori la
  IP de su interfaz interna, y debe aceptar las conexiones de midPoint que llegan
  por la red Docker. El riesgo de "escuchar en todas las interfaces" (que el servicio
  quede expuesto en una interfaz no deseada) **no se materializa** porque:
  1. El contenedor vive en una red Docker privada y segmentada (Fase 2); no hay
     interfaces "públicas" dentro de ese namespace de red.
  2. El puerto solo se publica al host de forma controlada en el docker-compose.
  3. Cada petición exige el token `X-Auth-Token` (defensa en profundidad).
- **Decisión:** Riesgo **aceptado y documentado** (residual). En un endurecimiento
  posterior podría limitarse a la IP interna del contenedor, aunque rompería la
  portabilidad entre entornos.

## Resumen final de hotspots/issues para el dashboard "reviewed"
| Item | Tipo | Severidad | Decisión |
|---|---|---|---|
| CSRF en Flask | Hotspot | Alta | Safe (API M2M, sin sesiones de navegador) |
| host 0.0.0.0 (permission) | Hotspot | Media | Acknowledged (necesario en Docker) |
| Encryption sensitive data | Hotspot | Baja | Acknowledged (red privada + TLS perimetral) |
| Bind all interfaces | Issue | Blocker | Riesgo aceptado documentado (mitigado por red+token) |
