# 🖥️ Primer acceso a la GUI de FreePBX — Fase 2

## 1. Levantar la pila

```bash
docker compose up -d
```

⏳ **Paciencia en el primer arranque:** FreePBX instala y registra todos sus
módulos contra la BD externa la primera vez. Puede tardar **5 a 10 minutos**.
Verifica el progreso con:

```bash
docker compose logs -f freepbx
```

Cuando veas que Apache está sirviendo y los módulos terminaron de instalarse,
ya puedes entrar.

## 2. Acceder a la interfaz web

Abre en el navegador:

```
http://localhost        (puerto 80)
https://localhost       (puerto 443 — certificado autofirmado, acepta la advertencia)
```

## 3. Asistente de configuración inicial (solo la primera vez)

FreePBX **no trae credenciales por defecto**: el primer acceso muestra el
asistente *Initial Setup* donde TÚ creas la cuenta de administrador.

1. **Username:** define el usuario admin (ej. `admin_telesecure` — evita `admin` a secas).
2. **Password:** contraseña robusta (mín. 12 caracteres, mayúsculas, números y símbolos — ISO 27001 A.5.17).
3. **Notification email:** correo del equipo para alertas del sistema.
4. Confirma y entra a **FreePBX Administration** con esas credenciales.

## 4. Ajustes mínimos post-instalación

1. En el asistente inicial: configura idioma (`es`) y zona horaria (`America/Lima`).
2. Ve a **Settings → Asterisk SIP Settings**:
   - Verifica que el rango RTP sea **10000–10100** (coincide con los puertos publicados en el compose).
   - En *NAT Settings*, define la IP externa si harás pruebas desde fuera del host.
3. Pulsa el botón rojo **Apply Config** (arriba a la derecha) — ningún cambio
   se aplica a Asterisk hasta presionarlo.

## 5. Verificación rápida

```bash
# ¿Asterisk corre dentro del contenedor?
docker exec telesecure_freepbx asterisk -rx "core show version"

# ¿FreePBX está conectado a la MariaDB central (no embebida)?
docker exec telesecure_db mariadb -u fpbx_user -p'FreepbxCambiar123!' \
  -e "SHOW TABLES IN asterisk;" | head

# ¿Las tablas puente de midPoint existen y no tocan las de FreePBX?
docker exec telesecure_db mariadb -u mp_user -p'MidpointCambiar123!' \
  -e "SHOW TABLES IN midpoint_integration;"
```

Si los tres comandos responden, la Fase 2 está operativa. ✅

> 💡 Para la demo: crea una extensión de prueba en
> **Applications → Extensions → Add New SIP (chan_pjsip) Extension**
> (ej. 1001) y regístrala con Zoiper/MicroSIP apuntando a `localhost:5060`.
