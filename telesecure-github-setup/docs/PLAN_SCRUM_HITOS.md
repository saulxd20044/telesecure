# Plan Scrum e Hitos del Proyecto

Documento de gestión del proyecto TeleSecure bajo el marco Scrum, adaptado a un
equipo reducido de desarrollo. Complementa el backlog definido en
`docs/HISTORIAS_USUARIO.md` y establece la relación entre sprints, hitos de
GitHub (milestones) y entregables del ciclo de vida (SDLC) ya documentados en
el README del proyecto.

Duración de cada sprint: una semana. Cada sprint corresponde a un milestone en
el repositorio.

---

## 1. Roles del equipo

| Rol | Responsable | Función |
|---|---|---|
| Product Owner | Autor del proyecto | Prioriza el backlog y valida el cumplimiento de cada historia de usuario (HU) |
| Scrum Master | Autor del proyecto | Da seguimiento a la cadencia del sprint y resuelve bloqueos |
| Equipo de desarrollo | Autor / colaboradores | Implementa infraestructura, integración, seguridad y documentación |
| Interesado (stakeholder) | Docente / evaluador | Revisa el resultado de cada sprint contra los criterios de evaluación |

---

## 2. Backlog de producto

El backlog se mantiene como fuente única en `docs/HISTORIAS_USUARIO.md`, con el
formato "Como / quiero / para" y criterios de aceptación verificables,
trazados a controles de ISO/IEC 27001 e ISO/IEC 25010.

Cada historia de usuario debe registrarse como un Issue del repositorio,
manteniendo el mismo identificador (HU-01, HU-02, etc.) para conservar la
trazabilidad entre historia, commit, pull request y milestone.

Convención de título de Issue: `[HU-0X] Descripción breve`.

---

## 3. Sprints e hitos

| Sprint | Milestone | Objetivo | Rama de trabajo | Criterio de cierre |
|---|---|---|---|---|
| 1 | Sprint 1 - Fundacional | Backlog e infraestructura base reproducible | `feature/infra-base` | `docker compose up -d` levanta los cinco contenedores sin intervención manual |
| 2 | Sprint 2 - Despliegue | PBX e IAM accesibles en la VM | `feature/despliegue-vm` | Interfaz de FreePBX y consola de midPoint operativas; audio RTP verificado |
| 3 | Sprint 3 - Integración | Flujo automático de rol a extensión SIP | `feature/provisioning-webhook` | La asignación del rol AgenteCallCenter en midPoint crea la extensión en FreePBX sin intervención manual |
| 4 | Sprint 4 - Seguridad y Calidad | Auditoría conforme a ISO 27001 e ISO 25010 | `feature/auditoria-iso` | Reportes en `docs/FASE4_*` con hallazgos y plan de tratamiento |
| 5 | Sprint 5 - Documentación y Sustentación | Cumplimiento normativo y demostración de extremo a extremo | `feature/documentacion-final` | `docs/TABLA_CUMPLIMIENTO_ISO.md` y `docs/CUMPLIMIENTO_RUBRICA.md` completos; demostración disponible |

Los cinco milestones deben crearse en el repositorio (Issues > Milestones), con
la fecha límite ajustada al cronograma del curso.

---

## 4. Definición de terminado

Un Issue o historia de usuario se considera cerrado cuando se cumplen las
siguientes condiciones:

1. El código se desarrolla en una rama `feature/<nombre>`, nunca directamente
   en `main` o `develop`.
2. Los commits siguen la convención descrita en
   `docs/GUIA_RAMAS_Y_COMMITS.md`.
3. Se abre un Pull Request contra `develop`, utilizando la plantilla del
   repositorio y referenciando el Issue correspondiente (`Closes #N`).
4. La integración continua (workflow `ci.yml`) finaliza sin errores.
5. El Pull Request cuenta con al menos una revisión aprobada.
6. Tras el merge a `develop`, se incorpora la evidencia correspondiente en
   `docs/` (captura, log o reporte).
7. Al completarse todos los Issues del sprint, se abre un Pull Request de
   `develop` hacia `main`, se genera la etiqueta de versión (sección 6) y se
   cierra el milestone.

---

## 5. Tablero de seguimiento

Se recomienda un tablero Kanban en GitHub Projects con las siguientes columnas,
consistentes con el formato ya usado en `HISTORIAS_USUARIO.md`:

Backlog de producto | Backlog del sprint | En progreso | En revisión | Terminado

Automatizaciones sugeridas:
- Un Issue asignado al sprint activo pasa automáticamente a "Backlog del sprint".
- Un Pull Request vinculado mueve el Issue a "En revisión".
- El cierre del Issue o el merge del Pull Request lo mueve a "Terminado".

---

## 6. Versionado semántico por hito

Cada cierre de milestone corresponde a una etiqueta (tag) en `main`:

| Milestone | Etiqueta |
|---|---|
| Sprint 1 | v0.1.0-infra |
| Sprint 2 | v0.2.0-despliegue |
| Sprint 3 | v0.3.0-integracion |
| Sprint 4 | v0.4.0-auditoria |
| Sprint 5 | v1.0.0 |

```
git tag -a v0.3.0-integracion -m "Sprint 3: aprovisionamiento automatico de rol a extension SIP"
git push origin v0.3.0-integracion
```

Esta línea de tiempo queda disponible en la sección "Releases" del repositorio
y sirve como evidencia auditable para la sustentación y para el control de
cambios exigido por ISO/IEC 27001, cláusula A.8.32.
