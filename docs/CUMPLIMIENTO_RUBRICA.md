# Análisis de cumplimiento contra la rúbrica oficial
## Laboratorio de Integración de Sistemas — TeleSecure

> Mapeo punto por punto entre lo que pide el enunciado y lo implementado.
> Incluye notas de defensa para las decisiones que difieren del PDF.

## Criterios de Evaluación (tabla de la rúbrica)

| Criterio | Excelente (100%) | Estado TeleSecure | Veredicto |
|---|---|---|---|
| **Funcionamiento (Docker)** | Todos los contenedores inician en red propia y persisten datos | 5 contenedores en red `telesecure_net`, con volúmenes persistentes (PG, mariadb, midpoint_home) y `restart: unless-stopped` | ✅ EXCELENTE |
| **Integración (midPoint+Asterisk)** | midPoint provisiona activamente los usuarios en Asterisk vía API | Al asignar el rol AgenteCallCenter, midPoint dispara (notificador) un webhook que crea la extensión SIP vía **API GraphQL** de FreePBX, automáticamente | ✅ EXCELENTE |
| **Seguridad (ISO 27001)** | TLS en SIP + repositorio incluye análisis de vulnerabilidades | TLS 1.2 + SRTP forzado por extensión; Trivy sobre las 5 imágenes con plan de tratamiento | ✅ EXCELENTE |
| **Metodología y Calidad** | Git (commits por integrante) + pruebas automatizadas + SonarQube | 32 tests unitarios (corren en el build del Dockerfile) + SonarQube (Fiabilidad A, Mantenibilidad A) | ✅ EXCELENTE en pruebas y Sonar; ⚠️ Git por integrante depende del equipo |

## Diferencias respecto al PDF (y su justificación técnica)

### 1. Asterisk "puro" vs FreePBX
- **PDF pide:** imagen Asterisk personalizada sobre `debian:bullseye`, editando
  `pjsip.conf` directamente.
- **Implementado:** FreePBX 17 (que ES Asterisk + capa de gestión/GUI/API).
- **Defensa:** FreePBX usa Asterisk como motor (chan_pjsip). La integración vía
  **API GraphQL** es *superior* a editar `pjsip.conf` a mano: es transaccional,
  validada y genera el objeto `auth` correctamente. El PDF mismo dice "ejecute un
  comando o script que agregue la extensión" — el webhook hace exactamente eso,
  pero por API en vez de por archivo. Cumple el espíritu (provisión activa por API).

### 2. PostgreSQL para midPoint en vez de solo MariaDB
- **PDF pide:** MySQL o PostgreSQL; menciona `mariadb:10.6`.
- **Implementado:** MariaDB 10.6 para FreePBX **+** PostgreSQL 16 para midPoint.
- **Defensa:** midPoint 4.4+ abandonó el soporte de MariaDB; el repositorio nativo
  oficial de Evolveum **requiere** PostgreSQL. Usar PostgreSQL no es una desviación,
  es seguir la arquitectura soportada del producto. El PDF permite PostgreSQL
  explícitamente ("MySQL o PostgreSQL").

### 3. Disparo por notificador en vez de "Synchronization/proyección"
- **PDF pide:** configurar la proyección (Synchronization) para que al dar de alta
  un usuario con rol AgenteCallCenter, midPoint ejecute el script.
- **Implementado:** notificador (generalNotifier + customTransport) que detecta la
  asignación del rol y dispara el webhook.
- **Defensa:** ambos son mecanismos nativos de midPoint para reaccionar a eventos.
  El resultado pedido —"al asignar el rol AgenteCallCenter, se crea la extensión"—
  se cumple íntegramente. El notificador resultó el camino viable para invocar un
  endpoint HTTP externo de forma directa.

## Entregables exigidos (sección 6 del PDF) — checklist

| # | Entregable | Estado | Dónde |
|---|---|---|---|
| 1 | Diagrama de arquitectura (contenedores, puertos, flujo) | ⏳ Por incluir en informe | (generar) |
| 2 | Evidencias de configuración (compose corriendo, log midPoint, softphone registrado) | ✅ Capturas tomadas | tu PC |
| 3 | Prueba de Concepto: video 2-3 min de llamada entre 2 softphones | ⏳ Por grabar | (Fase 5) |
| 4 | Análisis de cumplimiento: tabla componente ↔ cláusula ISO 27001 + métricas 25010 | ✅ Ver TABLA_CUMPLIMIENTO_ISO.md | docs/ |

## Puntos fuertes para destacar en la sustentación
1. **Integración activa por API** (no edición manual de archivos) — supera el mínimo.
2. **Auditoría de seguridad completa** (4 controles con evidencia real).
3. **Componente propio con calidad A/A** en SonarQube.
4. **Provisión automática end-to-end demostrable** en vivo (el video estrella).

## Punto a reforzar (honestidad)
- **Git con commits por integrante:** la rúbrica lo evalúa. Si el repo se trabajó
  mayormente en una cuenta, conviene que cada integrante haga al menos algunos
  commits significativos antes de la entrega, o documentar la distribución de trabajo.
- **CDR (registro de llamadas):** el PDF menciona verificar que el CDR se guarda en BD.
  FreePBX genera CDRs nativamente (módulo CDR Reports en la GUI) — vale la pena
  capturar esa pantalla tras una llamada como evidencia adicional.
