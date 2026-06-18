# 📋 Historias de Usuario — Fase 1 (Tablero Kanban)

> Backlog priorizado del Sprint 1. Formato: *Como [rol], quiero [funcionalidad], para [beneficio]*, con criterios de aceptación verificables (Definition of Done) alineados a ISO/IEC 27001 y 25010.

---

## 🗂️ Tablero

| 🔴 Backlog | 🟡 En progreso | 🟢 Hecho |
|---|---|---|
| HU-03 | HU-02 | HU-01 |

---

## HU-01 — Autenticación segura del agente en la PBX

**Como** agente de telecomunicaciones,
**quiero** autenticarme en la central Asterisk con credenciales SIP individuales y gestionadas centralmente,
**para** que solo personal autorizado realice y reciba llamadas, garantizando la trazabilidad de cada extensión.

**Criterios de aceptación:**
- [ ] Cada agente posee una extensión SIP única (no hay credenciales compartidas) — *ISO 27001 A.5.16*.
- [ ] El registro SIP falla con credenciales inválidas y el intento queda registrado en los logs de Asterisk — *A.8.15*.
- [ ] El contenedor Asterisk expone el puerto 5060/UDP y el rango RTP 10000-10100/UDP, y un softphone de prueba logra registrarse exitosamente.

**Prioridad:** Alta · **Estimación:** 5 pts · **Etiquetas:** `seguridad` `asterisk` `fase-1`

---

## HU-02 — Aprovisionamiento centralizado de identidades

**Como** administrador de identidades (IAM),
**quiero** gestionar el alta, modificación y baja de los agentes desde la consola web de midPoint,
**para** eliminar cuentas huérfanas y asegurar que los derechos de acceso reflejen siempre la situación laboral real del agente.

**Criterios de aceptación:**
- [ ] midPoint se despliega vía Docker Compose y su consola web responde en el puerto 8080.
- [ ] midPoint persiste su repositorio en la base de datos MariaDB 10.6 a través de una red interna no expuesta al exterior — *ISO 27001 A.8.22*.
- [ ] Es posible crear un usuario de prueba con rol "Agente" desde la consola y el evento queda auditado — *A.5.18, A.8.15*.

**Prioridad:** Alta · **Estimación:** 8 pts · **Etiquetas:** `iam` `midpoint` `fase-1`

---

## HU-03 — Infraestructura reproducible y segmentada

**Como** arquitecto DevOps del proyecto,
**quiero** orquestar toda la plataforma (BD, midPoint y Asterisk) con un único `docker-compose.yml` con redes segmentadas, volúmenes persistentes y healthchecks,
**para** garantizar despliegues reproducibles, mantenibles y portables conforme a ISO/IEC 25010.

**Criterios de aceptación:**
- [ ] `docker compose up -d` levanta los tres servicios sin intervención manual — *25010: Portabilidad*.
- [ ] La base de datos vive en una red `internal: true` y no publica el puerto 3306 al host — *27001 A.8.20*.
- [ ] midPoint declara `depends_on` con condición de salud (`service_healthy`) sobre la BD — *25010: Fiabilidad*.
- [ ] Los datos de MariaDB, midPoint y la configuración de Asterisk sobreviven a un `docker compose down` (volúmenes nombrados) — *25010: Fiabilidad/Mantenibilidad*.

**Prioridad:** Crítica · **Estimación:** 5 pts · **Etiquetas:** `devops` `docker` `fase-1`
