# 🔒 Fase 4 — Auditoría de Seguridad y Calidad

> Proyecto TeleSecure · Controles ISO/IEC 27001:2022 e ISO/IEC 25010
> Rol: Auditor de Seguridad · Toda actividad debe generar **evidencia archivable** en `./evidencia/`

```bash
mkdir -p evidencia   # PowerShell: mkdir evidencia
```

---

## 1. TLS + SRTP para extensiones SIP desde la GUI de FreePBX

**Controles:** ISO 27001 A.8.24 (uso de criptografía) · ISO 25010: Seguridad/Confidencialidad
**Objetivo:** cifrar la señalización SIP (TLS) y el audio (SRTP) sin editar archivos `.conf`.

### Paso A — Generar el certificado

1. Menú **Admin → Certificate Management**.
2. Clic en **+ New Certificate → Generate Self-Signed Certificate**.
   - *Host name:* el nombre/IP con el que los softphones alcanzan la PBX (ej. `pbx.telesecure.local`).
   - *Description:* `cert-tls-telesecure-fase4`.
3. **Generate Certificate** y márcalo como **Default** (icono de check en la lista).

> 📌 *Para la sustentación:* autofirmado es aceptable en laboratorio; en producción se usaría Let's Encrypt (la misma pantalla tiene la pestaña para ello). Mencionar este tradeoff suma.

### Paso B — Habilitar el transporte TLS de chan_pjsip

1. Menú **Settings → Asterisk SIP Settings**.
2. Pestaña **SIP Settings [chan_pjsip]**.
3. En la sección de transportes, activa **`0.0.0.0 – tls`**:
   - *Port to Listen On:* `5061`
   - *Certificate Manager:* selecciona `cert-tls-telesecure-fase4`
   - *SSL Method:* `tlsv1_2` (no aceptar SSLv3/TLS1.0 — requisito de cifrado vigente)
   - *Verify Client / Verify Server:* `No` (con autofirmado; documentarlo como limitación)
4. **Submit**.

### Paso C — Forzar TLS + SRTP por extensión

Para **cada** extensión (ej. la 1001 creada por el webhook):

1. **Applications → Extensions →** clic en la extensión **→ pestaña Advanced**.
2. En la sección *Device Options / chan_pjsip*:
   - **Transport:** `0.0.0.0 – tls` ← esto **fuerza** TLS: la extensión deja de aceptar UDP/TCP plano.
   - **Media Encryption:** `SRTP via in-SDP` ← cifra el audio, no solo la señalización.
3. **Submit**.

### Paso D — Aplicar y publicar el puerto

1. Botón rojo **Apply Config**.
2. Añadir en el `docker-compose.yml` (servicio freepbx): `- "5061:5061/tcp"` y `docker compose up -d`.

### Paso E — Verificación y evidencia

```bash
# El transporte TLS debe aparecer escuchando en 5061
docker exec telesecure_freepbx asterisk -rx "pjsip show transports" \
  | tee evidencia/01_tls_transports.txt

# La extensión debe mostrar media_encryption: sdes y transport tls
docker exec telesecure_freepbx asterisk -rx "pjsip show endpoint 1001" \
  | tee evidencia/01_tls_endpoint_1001.txt
```

En el softphone (Zoiper/MicroSIP): servidor `IP:5061`, transporte **TLS**, aceptar el certificado autofirmado. Prueba negativa para el informe: intentar registrar la misma extensión por UDP **debe fallar** — captura de pantalla = evidencia de que TLS está *forzado*, no solo disponible.

---

## 2. Escaneo de vulnerabilidades de la imagen con Trivy

**Controles:** ISO 27001 A.8.8 (gestión de vulnerabilidades técnicas) · ISO 25010: Seguridad

Comando exacto (Linux/macOS, desde la raíz del proyecto):

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v trivy_cache:/root/.cache \
  -v "$(pwd)/evidencia:/evidencia" \
  aquasec/trivy:latest image \
  --scanners vuln \
  --severity CRITICAL,HIGH,MEDIUM \
  --output /evidencia/02_trivy_freepbx.txt \
  tiredofit/freepbx:latest
```

Variante **PowerShell** (Windows, Docker Desktop):

```powershell
docker run --rm `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -v trivy_cache:/root/.cache `
  -v "${PWD}\evidencia:/evidencia" `
  aquasec/trivy:latest image `
  --scanners vuln `
  --severity CRITICAL,HIGH,MEDIUM `
  --output /evidencia/02_trivy_freepbx.txt `
  tiredofit/freepbx:latest
```

Notas de auditor:

- El volumen `trivy_cache` evita re-descargar la BD de CVEs en cada corrida.
- La primera ejecución tarda varios minutos (descarga la base de vulnerabilidades).
- **Repite el comando** cambiando la imagen por `evolveum/midpoint:4.3`, `mariadb:10.6` y tu imagen del webhook → archivos `02_trivy_midpoint.txt`, etc. Auditar solo un contenedor es hallazgo en contra.
- Para el informe, agrega el resumen ejecutivo: total de CRITICAL/HIGH por imagen y el plan de tratamiento (actualizar tag, aceptar riesgo documentado, o mitigar). En una imagen "todo en uno" como FreePBX **van a salir muchas** — el valor auditor está en el análisis, no en el cero absoluto.

---

## 3. Análisis de calidad del código Python con SonarQube (efímero)

**Controles:** ISO 25010 — Mantenibilidad y Fiabilidad (ratings A-E de Sonar mapean directo)

### Paso A — Levantar SonarQube efímero

```bash
docker run -d --rm --name sonarqube_audit -p 9000:9000 sonarqube:community
```

(`--rm` = al detenerlo se autodestruye, sin residuos: efímero de verdad).
Espera 1-2 minutos y abre `http://localhost:9000` → login `admin` / `admin` → te obliga a cambiar la contraseña (eso ya es A.5.17 en acción, menciónalo).

### Paso B — Crear el proyecto y el token

1. **Create Project → Local project**: key `telesecure-webhook`, branch por defecto.
2. **Locally** → **Generate token** (ej. `audit-fase4`) → copia el token (`sqp_...`).

### Paso C — Ejecutar el scanner sobre los scripts de la Fase 3

Linux/macOS (desde la raíz del proyecto, donde está la carpeta `webhook/`):

```bash
docker run --rm \
  --network host \
  -e SONAR_HOST_URL="http://localhost:9000" \
  -e SONAR_TOKEN="sqp_TU_TOKEN_AQUI" \
  -v "$(pwd)/webhook:/usr/src" \
  sonarsource/sonar-scanner-cli \
  -Dsonar.projectKey=telesecure-webhook \
  -Dsonar.sources=. \
  -Dsonar.python.version=3.12 \
  -Dsonar.exclusions=__pycache__/**
```

PowerShell (Windows — `host.docker.internal` en lugar de `--network host`):

```powershell
docker run --rm `
  -e SONAR_HOST_URL="http://host.docker.internal:9000" `
  -e SONAR_TOKEN="sqp_TU_TOKEN_AQUI" `
  -v "${PWD}\webhook:/usr/src" `
  sonarsource/sonar-scanner-cli `
  -Dsonar.projectKey=telesecure-webhook `
  -Dsonar.sources=. `
  -Dsonar.python.version=3.12 `
  "-Dsonar.exclusions=__pycache__/**"
```

### Paso D — Leer resultados con ojos ISO 25010

En `http://localhost:9000` → proyecto `telesecure-webhook`:

| Métrica SonarQube | Característica ISO 25010 | Evidencia |
|---|---|---|
| Maintainability rating + Code Smells + Technical Debt | **Mantenibilidad** (modularidad, analizabilidad) | Captura del dashboard |
| Reliability rating + Bugs | **Fiabilidad** (madurez) | Captura del dashboard |
| Security Hotspots | Seguridad | Revisar c/u y marcarlo como revisado |
| Coverage | Capacidad de prueba | Mencionar los 32 tests unitarios |

Guarda capturas en `evidencia/03_sonarqube_*.png`. Al terminar:

```bash
docker stop sonarqube_audit   # --rm lo elimina automáticamente
```

> ⚠️ Al ser efímero, los resultados **se pierden al detenerlo**: toma las capturas ANTES de parar el contenedor.

---

## 4. Reporte de auditoría de inicios de sesión en midPoint

**Control:** ISO 27001 **A.8.15 (registro de eventos) / A.8.16 (monitoreo)**
midPoint audita nativamente cada sesión: no hay que configurar nada extra, solo **extraer y filtrar**.

### Opción A — Desde la GUI (visor de auditoría)

1. Login como `administrator` en `http://localhost:8080/midpoint`.
2. Menú lateral **Reports → Audit Log Viewer** (en 4.3 puede aparecer bajo *Server administration*).
3. Filtros:
   - **Event Type:** `Create session` → inicios de sesión (añade `Terminate session` para cierres).
   - **Outcome:** `Success` para logins correctos; repetir con `Fatal error` → **intentos fallidos** (lo más valioso para A.8.16: ahí se ven posibles ataques de fuerza bruta).
   - **From / To:** el periodo auditado.
4. Cada fila muestra: timestamp, iniciador, canal (GUI/REST), IP remota y resultado.
5. Captura de pantalla de ambos filtros → `evidencia/04_midpoint_logins_ok.png` y `04_midpoint_logins_fallidos.png`.

### Opción B — Reporte exportable (CSV) para anexar al informe

1. **Reports → All reports → New report** (tipo *Audit report* / colección de eventos de auditoría).
2. Configura la colección con el filtro `eventType = createSession`, columnas: timestamp, initiator, outcome, remote host.
3. **Save → Run report** → descarga el CSV desde **Reports → Created reports** → `evidencia/04_midpoint_audit_logins.csv`.

### Opción C — Evidencia directa desde la BD (la favorita del auditor)

La tabla `m_audit_event` del repositorio es la fuente primaria. Primero identifica cómo codifica tu versión los tipos de evento (se almacenan como enteros):

```bash
docker exec -it telesecure_db mariadb -u mp_user -p midpoint -e \
  "SELECT DISTINCT eventtype, COUNT(*) FROM m_audit_event GROUP BY eventtype;"
```

Luego, con el valor que corresponde a *create session* (compáralo contra lo que ves en el Audit Log Viewer para esa misma franja horaria), exporta:

```bash
docker exec -it telesecure_db mariadb -u mp_user -p midpoint -e \
  "SELECT timestampvalue AS fecha, initiatorname_orig AS usuario, \
          outcome, remotehostaddress AS ip_origen, sessionidentifier \
   FROM m_audit_event \
   WHERE eventtype = <VALOR_CREATE_SESSION> \
   ORDER BY timestampvalue DESC LIMIT 100;" \
  | tee evidencia/04_midpoint_audit_sql.txt
```

> 💡 Argumento para la defensa: la Opción C demuestra **no repudio** — el registro vive en la BD con timestamp e IP, fuera del alcance del usuario final, y el acceso a esa tabla está restringido por los usuarios segregados de la Fase 2.

---

## ✅ Checklist de cierre de la Fase 4

| # | Actividad | Control | Evidencia esperada |
|---|---|---|---|
| 1 | TLS forzado + SRTP en extensiones | A.8.24 / 25010-Seguridad | `01_tls_*.txt` + captura registro fallido por UDP |
| 2 | Escaneo Trivy (4 imágenes) | A.8.8 | `02_trivy_*.txt` + resumen de tratamiento |
| 3 | SonarQube sobre webhook Fase 3 | 25010 Mantenibilidad/Fiabilidad | Capturas dashboard + ratings |
| 4 | Auditoría de logins midPoint | A.8.15 / A.8.16 | CSV/SQL + capturas (éxitos y fallidos) |
