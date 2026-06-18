#!/usr/bin/env python3
# =====================================================================
# webhook_provisioner.py — Proyecto TeleSecure, Fase 3
#
# Servicio webhook que recibe eventos de midPoint y aprovisiona
# extensiones SIP (chan_pjsip) directamente en la base de datos de
# FreePBX (MariaDB), aplicando luego `fwconsole reload` para que
# Asterisk regenere su configuración sin reiniciar el contenedor.
#
# Flujo:
#   midPoint (rol AgenteCallCenter asignado)
#     └─ POST /provision  {oid, nombre, correo, extension?}
#          ├─ 1. Valida y formatea los datos (funciones puras, testeables)
#          ├─ 2. INSERT en FreePBX: tablas users, devices, sip (kv pjsip)
#          ├─ 3. INSERT en midpoint_integration (vínculo + bitácora)
#          └─ 4. docker exec telesecure_freepbx fwconsole reload
#
# Seguridad (ISO 27001):
#   - Autenticación por token compartido en cabecera X-Auth-Token (A.5.17)
#   - Toda operación queda en mp_log_aprovisionamiento (A.8.15)
#   - Consultas 100% parametrizadas: sin concatenación de SQL
# =====================================================================

import hmac
import logging
import os
import re
import secrets
import string
import subprocess

import pymysql
from flask import Flask, jsonify, request

# ----------------------------------------------------------------------
# Configuración (inyectada vía variables de entorno en docker-compose)
# ----------------------------------------------------------------------
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("WEBHOOK_DB_USER", "mp_user")
DB_PASS = os.environ.get("WEBHOOK_DB_PASSWORD", "")
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")
FREEPBX_CONTAINER = os.environ.get("FREEPBX_CONTAINER", "telesecure_freepbx")

# API GraphQL de FreePBX (forma soportada de crear extensiones).
# Desde el contenedor del webhook se usa el NOMBRE DE SERVICIO de FreePBX
# en la red Docker, no 'localhost' (que sería el propio webhook).
FREEPBX_API_BASE = os.environ.get("FREEPBX_API_BASE", "http://telesecure_freepbx")
FREEPBX_TOKEN_URL = os.environ.get(
    "FREEPBX_TOKEN_URL", f"{FREEPBX_API_BASE}/admin/api/api/token")
FREEPBX_GQL_URL = os.environ.get(
    "FREEPBX_GQL_URL", f"{FREEPBX_API_BASE}/admin/api/api/gql")
FREEPBX_CLIENT_ID = os.environ.get("FREEPBX_CLIENT_ID", "")
FREEPBX_CLIENT_SECRET = os.environ.get("FREEPBX_CLIENT_SECRET", "")

EXTENSION_MIN = 1001
EXTENSION_MAX = 1999
CONTEXTO_POR_DEFECTO = "from-internal"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("webhook_provisioner")

app = Flask(__name__)

# ======================================================================
# 1) FUNCIONES PURAS DE FORMATEO Y VALIDACIÓN  (cubiertas por unittest)
# ======================================================================

def validar_extension(extension) -> str:
    """Normaliza y valida una extensión SIP.

    Reglas:
      - Solo dígitos (se admite int o str).
      - Dentro del rango [EXTENSION_MIN, EXTENSION_MAX].
    Devuelve la extensión como string normalizado o lanza ValueError.
    """
    ext = str(extension).strip()
    if not re.fullmatch(r"\d+", ext):
        raise ValueError(f"Extensión inválida: '{extension}' (solo dígitos)")
    if not (EXTENSION_MIN <= int(ext) <= EXTENSION_MAX):
        raise ValueError(
            f"Extensión {ext} fuera del rango permitido "
            f"[{EXTENSION_MIN}-{EXTENSION_MAX}]"
        )
    return ext


def sanear_nombre(nombre: str) -> str:
    """Limpia el nombre para los campos descriptivos de FreePBX.

    - Elimina caracteres problemáticos para los archivos de configuración
      de Asterisk generados por FreePBX (comillas, corchetes, ; y saltos).
    - Colapsa espacios múltiples y recorta a 50 caracteres.
    """
    if not nombre or not str(nombre).strip():
        raise ValueError("El nombre del agente no puede estar vacío")
    limpio = re.sub(r"[\"'\[\];\r\n\\]", "", str(nombre))
    limpio = re.sub(r"\s+", " ", limpio).strip()
    return limpio[:50]


def validar_oid(oid: str) -> str:
    """Valida que el OID de midPoint tenga formato UUID (36 chars)."""
    patron = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    oid = str(oid).strip()
    if not re.fullmatch(patron, oid):
        raise ValueError(f"OID de midPoint inválido: '{oid}'")
    return oid.lower()


def generar_secret_sip(longitud: int = 24) -> str:
    """Genera una contraseña SIP criptográficamente segura (A.5.17).

    Garantiza presencia de minúscula, mayúscula y dígito; evita símbolos
    conflictivos con los archivos de configuración de Asterisk.
    """
    if longitud < 12:
        raise ValueError("El secret SIP debe tener al menos 12 caracteres")
    alfabeto = string.ascii_letters + string.digits
    while True:
        candidato = "".join(secrets.choice(alfabeto) for _ in range(longitud))
        if (any(c.islower() for c in candidato)
                and any(c.isupper() for c in candidato)
                and any(c.isdigit() for c in candidato)):
            return candidato


def construir_payload_extension(oid, nombre, correo, extension, secret) -> dict:
    """Construye el payload canónico ya validado/formateado.

    Esta es la 'frontera de calidad': todo dato que entra a la BD
    pasa primero por aquí. Es la función principal bajo unittest.
    """
    return {
        "midpoint_oid": validar_oid(oid),
        "nombre": sanear_nombre(nombre),
        "correo": (str(correo).strip().lower() if correo else None),
        "extension": validar_extension(extension),
        "secret": secret,
        "contexto": CONTEXTO_POR_DEFECTO,
    }


def filas_pjsip_para_sip_table(extension: str, secret: str) -> list:
    """Genera las filas keyword/data que FreePBX espera en su tabla `sip`
    (sí, la tabla se llama 'sip' aunque la tecnología sea pjsip) para
    una extensión chan_pjsip mínima funcional.

    Devuelve lista de tuplas (id, keyword, data, flags) lista para
    executemany() parametrizado.
    """
    pares = [
        ("secret", secret),
        ("dtmfmode", "rfc4733"),
        ("context", CONTEXTO_POR_DEFECTO),
        ("max_contacts", "1"),
        ("media_encryption", "no"),
        ("transport", "0.0.0.0-udp"),
        ("callerid", f"device <{extension}>"),
    ]
    return [(extension, kw, data, idx) for idx, (kw, data) in enumerate(pares)]


# ======================================================================
# 2) CAPA DE BASE DE DATOS (todo parametrizado)
# ======================================================================

def _conn(database: str):
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=database, charset="utf8mb4", autocommit=False,
    )


def insertar_extension_freepbx(p: dict) -> None:
    """Crea la extensión usando la API GraphQL oficial de FreePBX.

    A diferencia de la inyección SQL directa (no soportada), la API
    genera correctamente endpoint + aor + auth de chan_pjsip, por lo
    que el registro SIP funciona sin pasos manuales. Tras crear la
    extensión, dispara `doreload` para aplicar la configuración.
    """
    import requests

    # 1) Obtener token OAuth2 (modo client_credentials, máquina-a-máquina)
    tok = requests.post(
        FREEPBX_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": FREEPBX_CLIENT_ID,
            "client_secret": FREEPBX_CLIENT_SECRET,
        },
        timeout=15,
    )
    if tok.status_code != 200:
        raise RuntimeError(f"OAuth falló (HTTP {tok.status_code}): {tok.text[:200]}")
    access_token = tok.json().get("access_token")
    if not access_token:
        raise RuntimeError("OAuth no devolvió access_token")

    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json"}

    # 2) Mutación addExtension (FreePBX genera endpoint+aor+auth).
    #    El secret se pasa vía User Manager (umPassword) con umEnable=true,
    #    que es como esta versión de la API expone la contraseña SIP.
    mutation_add = """
    mutation ($extid: ID!, $name: String!, $secret: String!, $email: String!) {
      addExtension(input: {
        extensionId: $extid
        name: $name
        tech: "pjsip"
        umEnable: true
        umPassword: $secret
        email: $email
        vmEnable: false
        maxContacts: "1"
      }) { status message }
    }
    """
    r = requests.post(
        FREEPBX_GQL_URL, headers=headers,
        json={"query": mutation_add, "variables": {
            "extid": p["extension"], "name": p["nombre"],
            "secret": p["secret"],
            "email": p["correo"] or f"{p['extension']}@telesecure.local",
        }},
        timeout=30,
    )
    _validar_respuesta_gql(r, "addExtension")

    # 3) Aplicar la config de forma SÍNCRONA y garantizada.
    #    El doreload de GraphQL es asíncrono (devuelve antes de terminar),
    #    por lo que el objeto auth de pjsip puede no estar listo al volver.
    #    Ejecutamos `fwconsole reload` vía el socket Docker, que SÍ bloquea
    #    hasta que Asterisk regenera toda la configuración (incluido auth).
    _reload_sincrono()


def _reload_sincrono() -> str:
    """Ejecuta `fwconsole reload` dentro de FreePBX y espera a que termine."""
    import docker
    cliente = docker.from_env()
    contenedor = cliente.containers.get(FREEPBX_CONTAINER)
    codigo, salida = contenedor.exec_run(["fwconsole", "reload"], demux=False)
    texto = salida.decode("utf-8", errors="replace") if salida else ""
    if codigo != 0:
        raise RuntimeError(f"fwconsole reload falló (code={codigo}): {texto[:300]}")
    return texto[-300:]


def _validar_respuesta_gql(resp, operacion: str) -> None:
    """Verifica que la respuesta GraphQL no traiga errores."""
    if resp.status_code != 200:
        raise RuntimeError(f"{operacion}: HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"{operacion}: {data['errors']}")
    # addExtension/doreload devuelven status booleano dentro de data
    bloque = (data.get("data") or {}).get(operacion) or {}
    if bloque.get("status") is False:
        raise RuntimeError(f"{operacion} status=false: {bloque.get('message')}")


def eliminar_extension_freepbx(extension: str) -> None:
    """Elimina una extensión vía API GraphQL (deleteExtension + reload)."""
    import requests
    tok = requests.post(
        FREEPBX_TOKEN_URL,
        data={"grant_type": "client_credentials",
              "client_id": FREEPBX_CLIENT_ID,
              "client_secret": FREEPBX_CLIENT_SECRET},
        timeout=15,
    )
    access_token = tok.json().get("access_token")
    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json"}
    mut = """mutation ($extid: ID!) {
      deleteExtension(input: { extensionId: $extid }) { status message }
    }"""
    r = requests.post(FREEPBX_GQL_URL, headers=headers,
                      json={"query": mut, "variables": {"extid": extension}},
                      timeout=30)
    _validar_respuesta_gql(r, "deleteExtension")
    _reload_sincrono()


def registrar_vinculo_y_log(p: dict, operacion: str, resultado: str,
                            detalle: str = "") -> None:
    """Registra el vínculo identidad<->extensión y la bitácora (A.8.15)."""
    cn = _conn("midpoint_integration")
    try:
        with cn.cursor() as cur:
            if operacion == "ALTA" and resultado == "EXITO":
                cur.execute(
                    "INSERT INTO mp_identidad_extension "
                    "(midpoint_oid, nombre_completo, correo, extension_sip, "
                    " rol_id, estado) "
                    "VALUES (%s, %s, %s, %s, "
                    " (SELECT id FROM mp_rol_telefonia WHERE codigo='AGENTE'),"
                    " 'ACTIVO')",
                    (p["midpoint_oid"], p["nombre"], p["correo"],
                     p["extension"]),
                )
            cur.execute(
                "INSERT INTO mp_log_aprovisionamiento "
                "(midpoint_oid, extension_sip, operacion, resultado, detalle) "
                "VALUES (%s, %s, %s, %s, %s)",
                (p["midpoint_oid"], p["extension"], operacion,
                 resultado, detalle[:1000]),
            )
        cn.commit()
    finally:
        cn.close()


def extension_disponible(extension: str) -> bool:
    cn = _conn("asterisk")
    try:
        with cn.cursor() as cur:
            cur.execute("SELECT 1 FROM devices WHERE id = %s", (extension,))
            return cur.fetchone() is None
    finally:
        cn.close()


def siguiente_extension_libre() -> str:
    """Asigna la primera extensión libre del rango (asignación automática)."""
    cn = _conn("asterisk")
    try:
        with cn.cursor() as cur:
            cur.execute(
                "SELECT id FROM devices WHERE id REGEXP '^[0-9]+$'")
            usadas = {int(r[0]) for r in cur.fetchall()}
    finally:
        cn.close()
    for n in range(EXTENSION_MIN, EXTENSION_MAX + 1):
        if n not in usadas:
            return str(n)
    raise RuntimeError("No quedan extensiones libres en el rango")


# ======================================================================
# 3) APLICACIÓN DE CAMBIOS EN CALIENTE
# ======================================================================

def aplicar_fwconsole_reload() -> str:
    """Ejecuta `fwconsole reload` DENTRO del contenedor FreePBX usando la
    librería Docker de Python (habla con /var/run/docker.sock directamente,
    sin depender del binario `docker` en el contenedor del webhook).

    Nota de riesgo documentada: montar el socket de Docker otorga
    privilegios amplios; aceptable en laboratorio académico, en
    producción se reemplazaría por la API GraphQL de FreePBX.
    """
    import docker  # cliente Docker SDK para Python
    cliente = docker.from_env()
    contenedor = cliente.containers.get(FREEPBX_CONTAINER)
    codigo, salida = contenedor.exec_run(["fwconsole", "reload"], demux=False)
    texto = salida.decode("utf-8", errors="replace") if salida else ""
    if codigo != 0:
        raise RuntimeError(f"fwconsole reload falló (code={codigo}): {texto[:300]}")
    return texto[-300:]


# ======================================================================
# 4) ENDPOINTS HTTP
# ======================================================================

def _autorizado(req) -> bool:
    token = req.headers.get("X-Auth-Token", "")
    return bool(WEBHOOK_TOKEN) and hmac.compare_digest(token, WEBHOOK_TOKEN)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/provision", methods=["POST"])
def provision():
    """Llamado por midPoint al asignar el rol AgenteCallCenter."""
    if not _autorizado(request):
        return jsonify({"error": "no autorizado"}), 401

    datos = request.get_json(silent=True) or {}
    log.info("DIAGNOSTICO payload recibido: %r", datos)
    try:
        extension = datos.get("extension") or siguiente_extension_libre()
        secret = generar_secret_sip()
        payload = construir_payload_extension(
            oid=datos.get("oid", ""),
            nombre=datos.get("nombre", ""),
            correo=datos.get("correo"),
            extension=extension,
            secret=secret,
        )
    except ValueError as e:
        log.warning("Payload rechazado: %s", e)
        return jsonify({"error": str(e)}), 400

    if not extension_disponible(payload["extension"]):
        return jsonify({"error": f"La extensión {payload['extension']} ya existe"}), 409

    try:
        insertar_extension_freepbx(payload)
        registrar_vinculo_y_log(payload, "ALTA", "EXITO",
                                "extensión creada vía API GraphQL")
        log.info("Extensión %s creada para OID %s",
                 payload["extension"], payload["midpoint_oid"])
        # El secret se devuelve UNA sola vez para entregarlo al agente.
        return jsonify({
            "resultado": "EXITO",
            "extension": payload["extension"],
            "sip_secret": payload["secret"],
            "servidor_sip": "telesecure_freepbx:5060",
        }), 201
    except Exception as e:
        log.exception("Fallo en aprovisionamiento")
        try:
            registrar_vinculo_y_log(payload, "ALTA", "ERROR", str(e))
        except Exception:
            log.exception("No se pudo registrar el error en bitácora")
        return jsonify({"error": "fallo interno de aprovisionamiento"}), 500


@app.route("/deprovision", methods=["POST"])
def deprovision():
    """Llamado por midPoint al retirar el rol (baja de extensión)."""
    if not _autorizado(request):
        return jsonify({"error": "no autorizado"}), 401
    datos = request.get_json(silent=True) or {}
    try:
        oid = validar_oid(datos.get("oid", ""))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    cn = _conn("midpoint_integration")
    try:
        with cn.cursor() as cur:
            cur.execute(
                "SELECT extension_sip FROM mp_identidad_extension "
                "WHERE midpoint_oid = %s AND estado = 'ACTIVO'", (oid,))
            fila = cur.fetchone()
    finally:
        cn.close()
    if not fila:
        return jsonify({"error": "identidad sin extensión activa"}), 404
    ext = fila[0]

    # Baja de la extensión vía API GraphQL (incluye su propio reload)
    eliminar_extension_freepbx(ext)

    cn = _conn("midpoint_integration")
    try:
        with cn.cursor() as cur:
            cur.execute(
                "UPDATE mp_identidad_extension SET estado='DADO_DE_BAJA' "
                "WHERE midpoint_oid = %s", (oid,))
            cur.execute(
                "INSERT INTO mp_log_aprovisionamiento "
                "(midpoint_oid, extension_sip, operacion, resultado, detalle) "
                "VALUES (%s, %s, 'BAJA', 'EXITO', 'baja por retiro de rol')",
                (oid, ext),
            )
        cn.commit()
    finally:
        cn.close()

    return jsonify({"resultado": "EXITO", "extension_eliminada": ext}), 200


if __name__ == "__main__":
    if not WEBHOOK_TOKEN:
        raise SystemExit("Definir WEBHOOK_TOKEN antes de arrancar (A.5.17)")
    app.run(host="0.0.0.0", port=5000)
