import asyncio
import json
import re
import os
import jwt
import pymysql
from datetime import datetime, timedelta
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from panoramisk import Manager
from typing import Optional, List
import subprocess

# 1. Leer variables de entorno
AMI_HOST = os.getenv("AMI_HOST", "asterisk")
AMI_PORT = int(os.getenv("AMI_PORT", "5038"))
AMI_USER = os.getenv("AMI_USER", "admin")
AMI_SECRET = os.getenv("AMI_SECRET", "")

ami_manager = None

# 2. Gestionar el ciclo de vida de la aplicación (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ami_manager
    # Al arrancar la API: Conectamos de forma persistente a Asterisk AMI
    ami_manager = Manager(
        host=AMI_HOST,
        port=AMI_PORT,
        username=AMI_USER,
        secret=AMI_SECRET,
        ping_delay=10  # Envía un ping cada 10 segundos para mantener la conexión viva
    )
    try:
        await ami_manager.connect()
        print("✅ Conexión exitosa con el AMI de Asterisk / FreePBX")
    except Exception as e:
        print(f"❌ Error crítico al conectar con Asterisk AMI: {e}")
    
    yield
    
    # Al apagar la API: Cerramos la conexión limpiamente
    if ami_manager:
        ami_manager.close()
        print("🛑 Conexión con Asterisk AMI cerrada.")

app = FastAPI(lifespan=lifespan)

# Configuración de CORS para Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción define el origen exacto de Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "fpbx_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "FreepbxCambiar123!")
DB_NAME = os.getenv("DB_NAME", "asterisk")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key")

class LoginSchema(BaseModel):
    extension: str
    secret: str

def verify_extension_credentials(extension: str, secret: str) -> bool:
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # Query nativa para extraer el "secret" asignado a la extensión en FreePBX
            sql = "SELECT data FROM sip WHERE id = %s AND keyword = 'secret'"
            cursor.execute(sql, (extension,))
            result = cursor.fetchone()
            
            if result and result['data'] == secret:
                return True
            return False
    except Exception as e:
        print(f"Error conectando a MariaDB Asterisk: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# 3. Función para consultar los canales reales de Asterisk
async def get_real_asterisk_channels():
    global ami_manager
    # Eliminamos la verificación de ami_manager.connected (no existe)
    if not ami_manager:
        return []
    try:
        print("🔍 [DEBUG] Solicitando Action: Status...", flush=True)
        response = await ami_manager.send_action({'Action': 'Status'})
        if isinstance(response, list):
            print(f"📋 [DEBUG] Número de eventos en respuesta: {len(response)}")
        calls = []
        if isinstance(response, list):
            for evt in response:
                event_type = getattr(evt, 'Event', '')
                if event_type == 'Status':
                    channel = getattr(evt, 'Channel', '')
                    state = getattr(evt, 'ChannelStateDesc', '')
                    callerid = getattr(evt, 'CallerIDNum', '')
                    connected_line = getattr(evt, 'ConnectedLineNum', '')
                    duration = getattr(evt, 'Seconds', '0')
                    print(f"   📞 Canal encontrado: {channel}, Estado: {state}, Duration: {duration}")
                    try:
                        duration = int(duration) if str(duration).isdigit() else 0
                    except:
                        duration = 0
                    calls.append({
                        "id": channel,
                        "extension": connected_line or callerid,
                        "channel": channel,
                        "destination": connected_line or '',
                        "status": state,
                        "duration": duration,
                        "ai_status": "Escuchando flujo de audio..." if state == "Up" else "Llamada entrante..."
                    })
        print(f"✅ [DEBUG] Total de llamadas parseadas: {len(calls)}")
        return calls
    except Exception as e:
        print(f"❌ [DEBUG] Error en get_real_asterisk_channels: {e}")
        return []


@app.websocket("/api/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ [WS] Cliente conectado")
    try:
        while True:
            print("🔄 [WS] Consultando canales...")
            real_calls = await get_real_asterisk_channels()
            print(f"📤 [WS] Enviando {len(real_calls)} llamadas al frontend")
            try:
                await websocket.send_json(real_calls)
            except Exception as send_error:
                print(f"⚠️ [WS] Error al enviar: {send_error}")
                break
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        print("🛑 [WS] Cliente desconectado")
    except Exception as e:
        print(f"🚨 [WS] Error inesperado: {e}")
    finally:
        print("🔌 [WS] Conexión cerrada")

@app.post("/api/auth/login")
def login(data: LoginSchema):
    if not verify_extension_credentials(data.extension, data.secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Extensión o contraseña SIP incorrecta"
        )
    
    # Generar Token JWT válido por 8 horas
    token_payload = {
        "sub": data.extension,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
    
    return {"token": token, "extension": data.extension, "status": "success"}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

class CDRRecord(BaseModel):
    calldate: str
    src: str
    dst: str
    duration: int
    billsec: int
    disposition: str
    channel: str
    dstchannel: str
    uniqueid: str
    recordingfile: Optional[str] = None

@app.get("/api/cdr")
def get_cdr(
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    extension: Optional[str] = Query(None, description="Extensión origen o destino"),
    limit: int = Query(100, ge=1, le=1000, description="Máx. registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento")
):
    """
    Obtiene registros CDR filtrados por fecha, extensión y paginados.
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database='asteriskcdrdb',
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # Consulta base
            sql = """
                SELECT calldate, src, dst, duration, billsec, disposition,
                       channel, dstchannel, uniqueid, recordingfile
                FROM cdr
                WHERE 1=1
            """
            params = []

            if start_date:
                sql += " AND calldate >= %s"
                params.append(start_date + " 00:00:00")
            if end_date:
                sql += " AND calldate <= %s"
                params.append(end_date + " 23:59:59")
            if extension:
                sql += " AND (src = %s OR dst = %s)"
                params.extend([extension, extension])

            sql += " ORDER BY calldate DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            records = cursor.fetchall()

            # Convertir fechas a string ISO para JSON
            for rec in records:
                if isinstance(rec.get('calldate'), datetime):
                    rec['calldate'] = rec['calldate'].isoformat()

            return {
                "cdr": records,
                "total": len(records),
                "limit": limit,
                "offset": offset
            }
    except Exception as e:
        print(f"Error consultando CDR: {e}")
        return {"error": "No se pudo obtener el historial CDR"}
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()


@app.get("/api/transcriptions")
def obtener_transcripciones(limit: int = 20):
    """Retorna las últimas llamadas transcritas para el Dashboard"""
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database='asteriskcdrdb',
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # Traemos el uniqueid, fecha y el texto, ordenados por la más reciente
            sql = """
                SELECT uniqueid, calldate, transcription 
                FROM cdr_transcriptions 
                ORDER BY calldate DESC 
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            resultados = cursor.fetchall()
            return resultados
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Base de Datos: {str(e)}")
        
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()


async def obtener_extensiones_online():
    global ami_manager

    if ami_manager is None:
        return 0

    try:
        response = await ami_manager.send_action({
            "Action": "Command",
            "Command": "pjsip show contacts"
        })

        if hasattr(response, "Output"):
            if isinstance(response.Output, list):
                salida = "\n".join(response.Output)
            else:
                salida = str(response.Output)

        elif hasattr(response, "content"):
            salida = response.content

        else:
            salida = str(response)

        return sum(
            1
            for linea in salida.splitlines()
            if "Avail" in linea
        )

    except Exception as e:
        print(e)
        return 0

@app.get("/api/metrics")
async  def obtener_metricas_dashboard():
    try:
        metrics = {
            "total_extensions": 0,
            "connected_extensions": 0,
            "total_calls": 0,
            "answered_calls": 0,
            "failed_calls": 0,
            "avg_duration_seconds": 0,
            "calls_chart_data": [] # Datos limpios para los gráficos
        }

        # 1. Métricas de Extensiones (Base de Datos 'asterisk')
        conn_ast = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn_ast.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM devices")
            res = cursor.fetchone()
            metrics["total_extensions"] = res["total"] if res else 0
        conn_ast.close()

        # Extensiones conectadas en tiempo real
        metrics["connected_extensions"] = await obtener_extensiones_online()

        # 2. Métricas de Llamadas e Historial (Base de Datos 'asteriskcdrdb')
        conn_cdr = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database='asteriskcdrdb',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn_cdr.cursor() as cursor:
            # Totales generales del día/mes
            sql_generales = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN disposition = 'ANSWERED' THEN 1 ELSE 0 END) as answered,
                    SUM(CASE WHEN disposition IN ('NO ANSWER', 'FAILED', 'BUSY') THEN 1 ELSE 0 END) as failed,
                    ROUND(AVG(billsec), 1) as avg_duration
                FROM cdr 
                WHERE calldate >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """
            cursor.execute(sql_generales)
            res_gen = cursor.fetchone()
            if res_gen and res_gen["total"] > 0:
                metrics["total_calls"] = res_gen["total"]
                metrics["answered_calls"] = res_gen["answered"] or 0
                metrics["failed_calls"] = res_gen["failed"] or 0
                metrics["avg_duration_seconds"] = float(res_gen["avg_duration"] or 0)

            # 3. Datos agrupados por fecha para el GRÁFICO (Últimos 7 días)
            sql_grafico = """
                SELECT 
                    DATE_FORMAT(calldate, '%Y-%m-%d') as fecha,
                    COUNT(*) as cantidad,
                    SUM(CASE WHEN disposition = 'ANSWERED' THEN 1 ELSE 0 END) as contestadas
                FROM cdr
                WHERE calldate >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE_FORMAT(calldate, '%Y-%m-%d')
                ORDER BY fecha ASC
            """
            cursor.execute(sql_grafico)
            metrics["calls_chart_data"] = cursor.fetchall()

        conn_cdr.close()
        return metrics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recopilando métricas: {str(e)}")