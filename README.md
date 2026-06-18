# 📞 Proyecto TeleSecure
## Infraestructura Unificada de Comunicaciones y Gestión de Identidad

> Integración **FreePBX 17 (PBX/Asterisk) + midPoint 4.10 (IAM)** orquestada con
> **Docker Compose**, bajo **ISO/IEC 27001:2022** e **ISO/IEC 25010**.
>
> Caso de uso central: *al asignar el rol **AgenteCallCenter** a un usuario en
> midPoint, se aprovisiona automáticamente su extensión SIP en FreePBX* — provisión
> activa por API, demostrable de extremo a extremo.

---

## 1. Arquitectura

```
                        ┌─────────────────────────────┐
                        │      Docker Compose          │
                        │  (orquesta el ciclo de vida) │
                        └──────────────┬──────────────┘
                                       │   red: telesecure_net
        ┌──────────────┬───────────────┼───────────────┬──────────────────┐
        ▼              ▼               ▼               ▼                  ▼
 ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
 │ telesecure │ │ telesecure │ │ telesecure   │ │ telesecure   │ │ telesecure   │
 │   _db      │ │_midpoint   │ │  _midpoint   │ │  _freepbx    │ │  _webhook    │
 │ MariaDB10.6│ │  _data     │ │ midPoint4.10 │ │ FreePBX 17   │ │ Flask + API  │
 │ (FreePBX)  │ │PostgreSQL16│ │   (IAM)      │ │ (Asterisk)   │ │ aprovision.  │
 └────────────┘ │ (midPoint) │ └──────────────┘ └──────────────┘ └──────────────┘
                └────────────┘
  (+ telesecure_midpoint_init: contenedor efímero que inicializa el repo de midPoint)

FLUJO DE PROVISIÓN:
  Admin asigna rol AgenteCallCenter en midPoint
     → notificador (generalNotifier + customTransport Groovy) detecta el evento
     → HTTP POST {oid,nombre,correo} + X-Auth-Token  →  Webhook /provision
     → Webhook llama API GraphQL de FreePBX (OAuth2)  →  crea extensión SIP
     → fwconsole reload  →  Softphone se registra (TLS 5061) → llamada SRTP
```

**Puertos del host:** FreePBX GUI `8090`, midPoint `8081`, SIP `5060/udp` y
`5061/tls`, RTP `10000-10100`.

---

## 2. Componentes (5 contenedores)

| Contenedor | Imagen | Rol | Puerto |
|---|---|---|---|
| `telesecure_db` | `mariadb:10.6` | BD de FreePBX | 3306 |
| `telesecure_midpoint_data` | `postgres:16-alpine` | BD de midPoint (repositorio nativo) | 5432 |
| `telesecure_midpoint` | `evolveum/midpoint:latest-alpine` | IAM / gestión de identidades | 8081 |
| `telesecure_freepbx` | `blacksunsolutions/freepbx:latest` | PBX (Asterisk + GUI + API) | 8090 |
| `telesecure_webhook` | `telesecure-webhook` (build local) | Conector de aprovisionamiento | 5000 |

> `telesecure_midpoint_init` corre una vez (inicializa el esquema de midPoint en
> PostgreSQL) y termina con exit 0 — es el comportamiento esperado.

---

## 3. Requisitos previos

- Docker Engine ≥ 24.x y Docker Compose v2 (`docker compose version`).
- **6 GB de RAM libres** mínimo (midPoint + FreePBX son exigentes).
- Windows: Docker Desktop con WSL2.
- Puertos libres en el host: `8090`, `8081`, `5060`, `5061`, `10000-10100`.

---

## 4. Despliegue

### Paso 1 — Variables de entorno
```bash
cp .env.example .env        # PowerShell: copy .env.example .env
```
Edita `.env` y cambia **todas** las contraseñas y el token:
```bash
openssl rand -hex 24        # → pégalo en WEBHOOK_TOKEN
```

### Paso 2 — Levantar la pila
```bash
docker compose up -d --build
```
Construye la imagen del webhook (corriendo sus **32 tests** en el build) y arranca
los servicios. **El primer arranque tarda** (midPoint ~2-3 min, FreePBX ~5-10 min).

### Paso 3 — Verificar
```bash
docker compose ps           # esperar 5 contenedores healthy (init en exit 0)
```

### Paso 4 — Primer acceso a FreePBX
Abre `http://localhost:8090`, completa el asistente, crea el usuario admin.
Habilita el módulo **API** (Admin → API) y crea una aplicación M2M (client_credentials)
para el webhook. Detalle en `docs/PRIMER_ACCESO_FREEPBX.md`.

### Paso 5 — Configurar midPoint
1. `http://localhost:8081/midpoint` (usuario `administrator`; contraseña en
   `docker compose logs telesecure_midpoint | grep -i password`).
2. **Importar objeto** → `midpoint/rol-agente-callcenter-4.10.xml` (Keep OID + Overwrite).
3. **System Configuration → Edit raw** → insertar el contenido de
   `midpoint/notificador-FUNCIONANDO-4.10.xml` (notificador + transporte).

### Paso 6 — Probar el flujo completo
Asigna el rol **AgenteCallCenter** a un usuario en midPoint. En segundos, la
extensión SIP aparece en FreePBX:
```bash
docker logs telesecure_webhook            # POST /provision 200 + extensión creada
docker exec telesecure_freepbx asterisk -rx "pjsip show auths"
```

---

## 5. Auditoría de seguridad y calidad (Fase 4)

Resultados completos en `docs/FASE4_*`. Resumen:

| Control | Herramienta | Resultado |
|---|---|---|
| A.8.8 Vulnerabilidades | Trivy (5 imágenes) | Hallazgos priorizados con plan de tratamiento |
| A.8.15/A.8.16 Auditoría | PostgreSQL `ma_audit_event` | Sesiones trazadas (quién/cuándo/IP/resultado) |
| ISO 25010 Calidad | SonarQube | Fiabilidad **A**, Mantenibilidad **A** |
| A.8.24 Criptografía | FreePBX/Asterisk | TLS 1.2 + SRTP forzado por extensión |

```bash
# verificación rápida del cifrado
docker exec telesecure_freepbx asterisk -rx "pjsip show transports"     # tls:5061
docker exec telesecure_freepbx asterisk -rx "pjsip show endpoint 1001"  # media_encryption: sdes
```

---

## 6. Mapa de fases (SDLC) → archivos

| Fase | Entregable | Archivos |
|---|---|---|
| 1 · Planificación | Backlog / historias de usuario | `docs/HISTORIAS_USUARIO.md` |
| 2 · Infraestructura | PBX + IAM + BD en Docker | `docker-compose.yml`, `db/init.sql`, `docs/PRIMER_ACCESO_FREEPBX.md` |
| 3 · Integración | Conector de aprovisionamiento | `webhook/*`, `midpoint/*.xml`, `db/grants-fase3.sql` |
| 4 · Seguridad/Calidad | Auditoría ISO | `docs/FASE4_*` |
| 5 · Documentación | Informe + PoC + cumplimiento | `docs/TABLA_CUMPLIMIENTO_ISO.md`, informe Word, video |

---

## 7. Cumplimiento normativo

- **`docs/TABLA_CUMPLIMIENTO_ISO.md`** — relación componente ↔ cláusula ISO 27001
  + métricas ISO 25010 (entregable #4 de la rúbrica).
- **`docs/CUMPLIMIENTO_RUBRICA.md`** — mapeo punto por punto contra el enunciado,
  con justificación de las decisiones de arquitectura.

---

## 8. Decisiones de ingeniería (para la sustentación)

- **FreePBX 17 en vez de Asterisk "pelado":** FreePBX *es* Asterisk + gestión + API.
  La provisión por **API GraphQL** es transaccional y validada (genera el objeto
  `auth` de chan_pjsip correctamente), superior a editar `pjsip.conf` a mano.
- **PostgreSQL para midPoint:** obligatorio desde midPoint 4.4 (Evolveum abandonó
  MariaDB). El enunciado permite PostgreSQL explícitamente.
- **Notificador en vez de proyección:** mecanismo nativo de midPoint para reaccionar
  a la asignación del rol e invocar el webhook HTTP. El resultado pedido se cumple.
- **Disparador midPoint→webhook:** la lógica vive en el `customTransport` (donde la
  variable `event` está disponible) y resuelve el usuario con
  `event.requestee.resolveObjectType()`. Ver `midpoint/SOLUCION_disparador_FINAL.md`.
- **Certificado TLS autofirmado:** válido para laboratorio; producción usaría una CA
  reconocida (Let's Encrypt, soportado por la misma pantalla de FreePBX).

---

## 9. Seguridad del repositorio

⚠️ El `.env`, `keystore_password.txt` y `repo_password.txt` contienen credenciales
de **laboratorio**. El `.gitignore` ya excluye `.env`. **No publiques credenciales
reales en repositorios públicos.**
