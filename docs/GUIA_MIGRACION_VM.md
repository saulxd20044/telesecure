# Guía de migración a VM Linux — Proyecto TeleSecure
## Objetivo: resolver el audio RTP usando network_mode: host (no disponible en Docker Desktop Windows)

> Esta guía lleva el proyecto desde Docker Desktop (Windows) a una VM Ubuntu en
> VirtualBox, donde Docker SÍ soporta host networking y el audio RTP funciona.
> El celular en la misma WiFi podrá llamar.

---

## ¿Por qué la VM resuelve el audio?

En Docker Desktop (Windows/WSL2), el `docker-proxy` reescribe la IP de origen de los
paquetes entrantes al gateway de Docker (172.21.0.1). Asterisk nunca ve la IP real
del softphone, por lo que el RTP no se enruta de vuelta. La solución, `network_mode:
host`, **no funciona en Docker Desktop para Windows**.

En una VM Ubuntu (Linux real), `network_mode: host` funciona: el contenedor comparte
directamente la interfaz de red de la VM, sin docker-proxy. Asterisk ve las IPs reales
y el RTP fluye.

---

## FASE A — Crear la VM en VirtualBox

1. **Nueva VM:**
   - Nombre: `telesecure-vm`
   - Tipo: Linux / Ubuntu (64-bit)
   - RAM: **8192 MB** (8 GB)
   - CPUs: **4** (mínimo 2)
   - Disco: **40 GB** dinámico

2. **CRÍTICO — Red en modo Bridged (antes de arrancar):**
   - VM seleccionada → Configuración → Red
   - Adaptador 1 → Conectado a: **"Adaptador puente"** (Bridged Adapter)
   - Nombre: tu tarjeta WiFi/Ethernet real (la que da internet)

   > El modo Bridged hace que la VM tenga su propia IP en tu red WiFi (ej.
   > 192.168.18.150), visible para el celular y la PC. Sin esto, el celular no
   > alcanza la PBX.

3. Montar la ISO de Ubuntu (Server o Desktop) y completar la instalación.
   - Usuario y contraseña que recuerdes (los usarás todo el tiempo).
   - Si es Server, marca "Install OpenSSH server" para administrarla cómodo por SSH.

---

## FASE B — Instalar Docker en Ubuntu

Una vez dentro de Ubuntu (terminal):

```bash
# Actualizar
sudo apt-get update && sudo apt-get upgrade -y

# Dependencias
sudo apt-get install -y ca-certificates curl gnupg git

# Repositorio oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker + Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Permitir usar docker sin sudo (cerrar y reabrir sesión después)
sudo usermod -aG docker $USER

# Verificar
docker --version
docker compose version
```

Cierra sesión y vuelve a entrar (o reinicia la VM) para que el grupo docker aplique.

---

## FASE C — Conocer la IP de la VM (la usarás en todo)

```bash
ip addr show | grep "inet "
```

Busca la IP del adaptador principal (NO 127.0.0.1, NO 172.x de Docker). Será algo
como `192.168.18.150`. **Anótala. La llamaremos IP_VM en esta guía.**

> Si la IP cambia entre reinicios, considera reservarla en tu router (DHCP estático)
> o configurar IP fija en Ubuntu. Para pruebas puntuales, basta con verificarla cada vez.

---

## FASE D — Llevar el proyecto a la VM

Opción 1 — Git (si lo subiste a un repo):
```bash
git clone TU_REPO telesecure
cd telesecure
```

Opción 2 — Copiar el ZIP (con carpeta compartida de VirtualBox o por SSH/scp):
```bash
# Si usas SSH desde Windows (PowerShell):
#   scp "D:\Descargas 2\telesecure-completo.zip" usuario@IP_VM:~/
unzip telesecure-completo.zip
cd telesecure
```

---

## FASE E — Ajustar el compose para host networking

El cambio clave está en el servicio **FreePBX**. Con `network_mode: host`:
- Se ELIMINA la sección `ports:` (ya no se publican; comparte la red de la VM).
- Se ELIMINA la sección `networks:` de FreePBX.
- `DBHOST` cambia de `db` a `127.0.0.1` (host networking no resuelve el DNS de Docker).
- Hay que exponer la BD al host para que FreePBX la alcance.

### E.1 — Editar el servicio db (exponer puerto al host)
En el servicio `db`, asegúrate de que tenga `ports`:
```yaml
  db:
    # ...
    ports:
      - "3306:3306"
    networks:
      - red_datos
```

### E.2 — Editar el servicio freepbx
Reemplaza la sección de red de FreePBX. Queda así:
```yaml
  freepbx:
    image: blacksunsolutions/freepbx:latest
    container_name: telesecure_freepbx
    restart: unless-stopped
    network_mode: host          # <<< CLAVE: comparte la red de la VM
    depends_on:
      db:
        condition: service_healthy
    environment:
      TZ: America/Lima
      DBENGINE: mysql
      DBHOST: 127.0.0.1         # <<< cambia de 'db' a 127.0.0.1
      DBPORT: "3306"
      DBNAME: asterisk
      CDRDBNAME: asteriskcdrdb
      DBUSER: ${FREEPBX_DB_USER:-fpbx_user}
      DBPASS: ${FREEPBX_DB_PASSWORD:-FreepbxCambiar123!}
      DB_USER: ${FREEPBX_DB_USER:-fpbx_user}
      DB_PASS: ${FREEPBX_DB_PASSWORD:-FreepbxCambiar123!}
      # ... (resto de variables AST* igual)
    volumes:
      - freepbx_varlib:/var/lib/asterisk
      - freepbx_etc:/etc/asterisk
      - freepbx_usrlib:/usr/lib64/asterisk
      - freepbx_logs:/var/log/asterisk
      - freepbx_www:/var/www/html
    # SIN sección 'ports:' (host networking expone todo directo)
    # SIN sección 'networks:'
    healthcheck:
      test: ["CMD-SHELL", "fwconsole --version > /dev/null 2>&1 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 300s
```

### E.3 — Ajustar el webhook (alcanzar FreePBX por IP de la VM)
El webhook llegaba a FreePBX por `http://telesecure_freepbx` (DNS de Docker). Ahora
FreePBX está en host networking, así que el webhook lo alcanza por la IP de la VM:
```yaml
  webhook:
    environment:
      # ...
      FREEPBX_API_BASE: http://IP_VM      # <<< reemplaza IP_VM por la real (ej. 192.168.18.150)
      FREEPBX_CONTAINER: telesecure_freepbx
```
> Nota: como el webhook sigue en red Docker y FreePBX en host, el webhook usa la IP
> de la VM para llegar a FreePBX. En Linux esto funciona directo.

---

## FASE F — Levantar la pila

```bash
docker compose up -d --build
docker compose ps          # esperar contenedores healthy (init en exit 0)
```

Primer arranque: midPoint ~2-3 min, FreePBX ~5-10 min. Paciencia.

---

## FASE G — Configurar FreePBX (NAT correcto para la VM)

1. Abre desde tu PC Windows: `http://IP_VM:80` (o el puerto que uses; con host
   networking FreePBX usa el 80 directo, ya no el 8090).
2. Completa el asistente inicial, habilita el módulo API, crea la app M2M.
3. **NAT Settings (Settings → Asterisk SIP Settings → chan_pjsip), transporte udp:**
   - **External Address:** la IP de la VM (IP_VM)
   - **Local Networks:** la red de tu LAN, ej. `192.168.18.0/24`
   > OJO: aquí SÍ va tu LAN como local (al revés que en Docker Desktop), porque ahora
   > Asterisk está directo en la red de la VM, sin doble NAT. Si el audio no fluye,
   > prueba dejando Local Networks vacío.
4. Crea las extensiones 1001-1005 (o impórtalas) y reaplica el TLS de la Fase 4.

---

## FASE H — Importar midPoint y probar

1. Importa el rol y el notificador (igual que en Windows):
   `midpoint/rol-agente-callcenter-4.10.xml` y `notificador-FUNCIONANDO-4.10.xml`.
   - El webhook URL en el notificador sigue siendo `http://telesecure_webhook:5000/provision`
     (webhook y midPoint siguen en red Docker, se ven por DNS).
2. Asigna el rol AgenteCallCenter → la extensión se crea sola.

---

## FASE I — Probar la llamada con audio (la prueba de fuego)

1. **En la PC (Windows):** configura MicroSIP/Zoiper apuntando a **IP_VM** (no 127.0.0.1).
   - Extensión 1002, su contraseña, transporte UDP.
2. **En el celular (misma WiFi):** configura un softphone apuntando a **IP_VM**.
   - Extensión 1003, su contraseña, UDP.
3. Verifica registros:
   ```bash
   docker exec telesecure_freepbx asterisk -rx "pjsip show endpoints"
   ```
   Los Contact ahora mostrarán las IPs reales (192.168.18.x), NO 172.21.0.1.
4. Llama 1002 ↔ 1003 y verifica audio.
5. Durante la llamada:
   ```bash
   docker exec telesecure_freepbx asterisk -rx "pjsip show channelstats"
   ```
   **Los contadores Receive/Transmit ahora deben SUBIR de 0 = audio fluyendo.**

---

## FASE J (opcional) — Videollamada

FreePBX/Asterisk soporta video si los códecs están habilitados:
1. En la extensión (Advanced): Max video streams = 1, códec h264 permitido.
2. En Settings → Asterisk SIP Settings: habilitar códec de video (h264).
3. Usar softphones con soporte de video (Linphone es gratis y soporta video por SIP;
   Zoiper free no siempre). Linphone en PC y celular permite la videollamada.

---

## Resumen de cambios respecto a Windows

| Aspecto | Windows (Docker Desktop) | VM Linux |
|---|---|---|
| Red de FreePBX | bridge + ports publicados | network_mode: host |
| DBHOST | db (DNS Docker) | 127.0.0.1 |
| External Address | 192.168.18.211 (la PC) | IP de la VM |
| Local Networks | solo 172.x (Docker) | 192.168.x (LAN) |
| Audio RTP | no fluye (docker-proxy) | fluye (host networking) |
| Acceso GUI | localhost:8090 | IP_VM:80 |

> El resto del proyecto (XML de midPoint, webhook, SQL, documentación) se reutiliza
> sin cambios. Solo cambia la capa de red de FreePBX y las IPs del NAT.
