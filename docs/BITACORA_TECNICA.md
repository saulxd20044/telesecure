# Bitácora Técnica — Proyecto TeleSecure
## Registro de implementación, problemas resueltos y estado actual

> Documento de trazabilidad del trabajo realizado. Útil para el informe final,
> la sustentación, y como evidencia de la metodología (SDLC).

---

## 1. Resumen del sistema construido

Sistema integrado de telefonía IP + gestión de identidades, contenedorizado:

| Componente | Tecnología | Función |
|---|---|---|
| PBX | FreePBX 17 (Asterisk + chan_pjsip) | Central telefónica, extensiones SIP, CDR |
| IAM | midPoint 4.10 | Gestión de identidades, RBAC, auditoría |
| BD PBX | MariaDB 10.6 | Configuración de FreePBX |
| BD IAM | PostgreSQL 16 | Repositorio nativo de midPoint |
| Conector | Webhook Flask (Python) | Aprovisionamiento automático vía API GraphQL |
| Orquestación | Docker Compose | Ciclo de vida de los 5 contenedores |

**Caso de uso central (funcionando):** al asignar el rol *AgenteCallCenter* a un
usuario en midPoint, se crea automáticamente su extensión SIP en FreePBX.

---

## 2. Hitos completados

### Fase 1-2 — Infraestructura
- 5 contenedores en red Docker propia (`telesecure_net`), con volúmenes persistentes
  y política `restart: unless-stopped`.
- Migración a PostgreSQL para midPoint (obligatorio desde 4.4; MariaDB ya no soportada).
- Puertos: en la VM, FreePBX usa `network_mode: host` (GUI 80, SIP 5060/5061, RTP
  10000-10100 directos en la red de la VM); midPoint en 8081, expuesto vía Docker.

### Fase 3 — Integración IAM ↔ PBX (provisión automática)
- **Webhook de aprovisionamiento** (Flask): recibe POST con datos del usuario y crea
  la extensión vía **API GraphQL de FreePBX** (OAuth2 client_credentials).
- **Disparador en midPoint** (el problema más difícil del proyecto):
  - Mecanismo: `generalNotifier` + `customTransport` (script Groovy).
  - **Problema resuelto:** el OID del usuario no fluía al transport. La solución fue
    mover toda la lógica al `customTransport` (donde la variable `event` está
    disponible) y usar `event.requestee.resolveObjectType()` para obtener el UserType
    completo (OID, nombre, email).
  - **Verificado:** el webhook recibe el payload completo y crea la extensión. midPoint
    procesa de forma asíncrona (tarda segundos), pero completa correctamente.

### Fase 4 — Auditoría de seguridad y calidad (4/4 completa)
| Control | Herramienta | Resultado |
|---|---|---|
| A.8.8 Vulnerabilidades | Trivy (5 imágenes) | 970 hallazgos; FreePBX 84%; webhook el más limpio (11) |
| A.8.15/A.8.16 Auditoría | PostgreSQL `ma_audit_event` | 9 sesiones trazadas, 0 fallidas |
| ISO 25010 Calidad | SonarQube | Fiabilidad A, Mantenibilidad A; 4 hotspots revisados |
| A.8.24 Cifrado | FreePBX/Asterisk | TLS 1.2 + SRTP forzado (extensión 1001) |

### Fase 5 — Documentación
- README reescrito a la arquitectura real (4.10 + PostgreSQL + 5 contenedores + GraphQL).
- Tabla de cumplimiento ISO (componente ↔ cláusula 27001 + métricas 25010).
- Análisis de cumplimiento punto por punto contra la rúbrica.

---

## 3. Verificación de la telefonía — estado y hallazgos

### 3.1 Lo que FUNCIONA (verificado)
- **Registro centralizado:** las extensiones aprovisionadas se registran en la PBX.
  Verificado con `pjsip show endpoints` → estado "Not in use" (registrado).
- **Señalización SIP completa:** las llamadas se establecen correctamente entre
  extensiones. El softphone muestra la llamada conectada y el cronómetro corre.
  Verificado con `core show channels` → canales en estado "Up".
- **Llamadas contestadas:** el historial del softphone muestra "answered" en las
  llamadas entre 1002 y 1003.

### 3.2 Bug encontrado y CORREGIDO — puerto del transporte UDP
- **Síntoma:** tras la Fase 4 (TLS), las llamadas dejaron de registrar.
- **Causa raíz:** al configurar el transporte TLS, el transporte **UDP quedó
  escuchando en el puerto 5061** en lugar del 5060 estándar.
- **Diagnóstico:** `pjsip show transports` mostró `0.0.0.0-udp ... 0.0.0.0:5061`.
- **Solución:** corregir "Port to Listen On" del transporte udp a 5060 (GUI).
  Verificado: `0.0.0.0-udp udp ... 0.0.0.0:5060`. Registro restablecido.

### 3.3 Audio RTP — problema diagnosticado y RESUELTO (migración a Linux)

Durante el desarrollo en Docker Desktop (Windows) se detectó que el audio de las
llamadas no fluía pese a que la señalización SIP funcionaba. Tras un diagnóstico
exhaustivo se identificó la causa raíz y se aplicó la solución definitiva.

**Síntoma inicial (en Windows):** la llamada se establecía (señalización OK) pero no
había audio en ninguna dirección; `pjsip show channelstats` mostraba **0 paquetes
RTP** en ambos canales.

**Causa raíz (diagnóstico):** el `docker-proxy` de Docker Desktop sobre Windows/WSL2
reescribe la IP de origen de los paquetes entrantes al gateway de la red Docker
(172.21.0.1). Asterisk nunca ve la IP real del softphone, por lo que el RTP no se
enruta de vuelta. Se confirmó en foros oficiales de Asterisk y FreePBX que la única
solución de fondo es `network_mode: host`, **no disponible en Docker Desktop para
Windows** (solo en Linux nativo).

**Solución aplicada — migración a VM Ubuntu:** se desplegó el sistema sobre una VM
Ubuntu 24.04 (VirtualBox, red en modo puente) donde Docker sí soporta host
networking. El contenedor FreePBX se configuró con `network_mode: host`, eliminando
la capa de NAT intermedia. La configuración NAT se ajustó al nuevo entorno
(External Address = IP de la VM, Local Networks = LAN real).

**Resultado verificado (evidencia VM_08_AUDIO_channelstats.txt):** durante una
llamada entre extensiones, `pjsip show channelstats` muestra **705+ paquetes RTP en
recepción y transmisión, 0 perdidos (Lost: 0), jitter 0.001**. El audio fluye en
ambas direcciones con calidad perfecta. La llamada entre PC y dispositivo en la red
local funciona correctamente.

| Métrica RTP | Windows (Docker Desktop) | VM Linux (host networking) |
|---|---|---|
| Paquetes Receive | 0 | 705+ y subiendo |
| Paquetes Transmit | 0 | 708+ y subiendo |
| Pérdida | N/A (sin flujo) | 0% |
| Audio audible | No | Sí |

> **Valor para la sustentación:** el caso ilustra un ciclo completo de ingeniería:
> detección del fallo, diagnóstico con evidencia (channelstats, identificación del
> docker-proxy), investigación de la causa raíz en fuentes oficiales, evaluación de
> alternativas (FusionPBX, Kubernetes, nube, VM) y aplicación de la solución
> correcta. No es una limitación aceptada, sino un problema resuelto.

---

## 4. Comandos de verificación útiles

```bash
# Estado de contenedores
docker compose ps

# Transportes SIP (verificar UDP en 5060, TLS en 5061)
docker exec telesecure_freepbx asterisk -rx "pjsip show transports"

# Extensiones registradas
docker exec telesecure_freepbx asterisk -rx "pjsip show endpoints"

# Llamadas activas
docker exec telesecure_freepbx asterisk -rx "core show channels"

# Estadísticas RTP (audio) durante una llamada
docker exec telesecure_freepbx asterisk -rx "pjsip show channelstats"

# Cifrado de la extensión 1001 (TLS+SRTP)
docker exec telesecure_freepbx asterisk -rx "pjsip show endpoint 1001"

# Auditoría de logins en midPoint
docker exec telesecure_midpoint_data psql -U midpoint -d midpoint \
  -c "SELECT timestamp, initiatorname, outcome, remotehostaddress \
      FROM ma_audit_event WHERE eventtype='CREATE_SESSION' ORDER BY timestamp DESC;"
```

---

## 5. Mapa de extensiones

| Extensión | Transporte | Cifrado | Uso |
|---|---|---|---|
| 1001 | TLS (5061) | SRTP forzado | Evidencia de cifrado (Fase 4) |
| 1002 | UDP (5060) | No | Pruebas de llamada |
| 1003 | UDP (5060) | No | Pruebas de llamada |
| 1004 | UDP (5060) | No | Disponible |
| 1005 | UDP (5060) | No | Disponible |

> Nota: Zoiper free no soporta TLS, por lo que la 1001 (TLS) se usa como evidencia de
> configuración de cifrado; las pruebas de llamada se hacen con extensiones UDP.

---

## 6. Estado global del proyecto

| Área | Estado |
|---|---|
| Infraestructura Docker (5 contenedores) | ✅ Completo |
| Provisión automática midPoint → FreePBX | ✅ Completo y verificado |
| Auditoría Fase 4 (4 controles) | ✅ Completo |
| Documentación + cumplimiento ISO/rúbrica | ✅ Completo |
| Telefonía: registro + señalización + establecimiento | ✅ Verificado |
| Telefonía: audio RTP (VM Linux, host networking) | ✅ Funcionando (705+ pkts, 0 perdidos) |
| Video PoC + informe Word | ⏳ Pendiente (Fase 5) |
