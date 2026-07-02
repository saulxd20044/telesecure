import asyncio
import os
import pymysql
import json
import subprocess
from panoramisk import Manager
from vosk import Model, KaldiRecognizer
from pathlib import Path

print("⏳ Cargando modelo VOSK en memoria (Español)...")
# Carga el modelo descargado en el Dockerfile
vosk_model = Model("/app/vosk-model")
print("🚀 Motor Vosk listo para transcribir.")

# 🎛️ CONFIGURACIÓN DE CONEXIONES
AMI_CONFIG = {
    "host": "host.docker.internal",  # Sigue apuntando al Host porque FreePBX está en modo 'host'
    "port": 5038,
    "username": "bef782a3b0a2573b88d44582dfd09cd1",
    "secret": "adcc502b6ac18a1832a40a5cf6ccede0"
}

# Soporta dinámicamente tanto DB_PASS como DB_PASSWORD
db_password = os.getenv("DB_PASSWORD", os.getenv("DB_PASS", "FreepbxCambiar123!"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "user": os.getenv("DB_USER", "fpbx_user"),
    "password": db_password,
    "database": "asteriskcdrdb",
    "port": 3306
}

manager = Manager(**AMI_CONFIG)

def transcribir_con_vosk(ruta_audio):
    """Convierte el WAV al vuelo mediante FFmpeg y extrae el texto con Vosk"""
    comando_ffmpeg = [
        'ffmpeg', '-loglevel', 'quiet', '-i', ruta_audio,
        '-ar', '16000', '-ac', '1', '-f', 's16le', '-'
    ]
    
    proceso = subprocess.Popen(comando_ffmpeg, stdout=subprocess.PIPE)
    reconocedor = KaldiRecognizer(vosk_model, 16000)
    
    transcripcion_completa = []
    
    while True:
        data = proceso.stdout.read(4000)
        if len(data) == 0:
            break
        if reconocedor.AcceptWaveform(data):
            resultado = json.loads(reconocedor.Result())
            if resultado.get("text"):
                transcripcion_completa.append(resultado["text"])
                
    resultado_final = json.loads(reconocedor.FinalResult())
    if resultado_final.get("text"):
        transcripcion_completa.append(resultado_final["text"])
        
    return " ".join(transcripcion_completa)

async def procesar_transcripcion_post_llamada(uniqueid):
    """Busca el archivo de audio en el CDR, lo transcribe y lo inyecta en la DB"""
    await asyncio.sleep(2.5) # Breve pausa para asegurar el cierre y mezcla del .wav por Asterisk
    print(f"🔍 Buscando registro de audio para UniqueID: {uniqueid}")
    
    try:
        connection = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            # 1. Obtener el nombre del archivo grabado desde el CDR
            sql = "SELECT calldate, recordingfile FROM cdr WHERE uniqueid = %s"
            cursor.execute(sql, (uniqueid,))
            cdr_record = cursor.fetchone()
            
            if not cdr_record or not cdr_record['recordingfile']:
                print(f"⚠️ Llamada {uniqueid} no registra archivo de audio. Omitiendo.")
                return

            nombre_archivo = cdr_record['recordingfile']
            base_dir = Path("/var/spool/asterisk/monitor")
            
            # ✨ MEJORA: Búsqueda recursiva en subcarpetas Año/Mes/Día
            archivos_encontrados = list(base_dir.glob(f"**/{nombre_archivo}"))
            
            if not archivos_encontrados:
                print(f"❌ Archivo no accesible en volumen: {nombre_archivo} (Buscado recursivamente en {base_dir})")
                return
            
            # Tomamos la ruta absoluta real donde se encontró el archivo
            ruta_audio_real = str(archivos_encontrados[0])
            print(f"📂 Archivo localizado exitosamente en: {ruta_audio_real}")

            # 2. Transcribir localmente con Vosk
            print(f"🎙️ Transcribiendo con Vosk: {ruta_audio_real}")
            loop = asyncio.get_running_loop()
            texto_transcrito = await loop.run_in_executor(None, transcribir_con_vosk, ruta_audio_real)
            
            if not texto_transcrito.strip():
                print(f"⚠️ Transcripción vacía (no se detectó voz) para {uniqueid}")
                texto_transcrito = "[Llamada sin voz detectable / Silencio]"

            # 3. Guardar directamente en la nueva tabla para el Dashboard
            sql_insert = """
                INSERT INTO cdr_transcriptions (uniqueid, calldate, transcription)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE transcription = VALUES(transcription)
            """
            cursor.execute(sql_insert, (uniqueid, cdr_record['calldate'], texto_transcrito))
            connection.commit()
            print(f"✅ Transcripción guardada en DB para la llamada {uniqueid}")

    except Exception as e:
        print(f"❌ Error en el proceso de transcripción: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

@manager.register_event('Hangup')
def handle_hangup(manager, event):
    channel = event.get('Channel', '')
    if 'PJSIP/' in channel and '-with-exten' not in event.get('Context', ''):
        uniqueid = event.get('Uniqueid')
        print(f"\n📞 Cuelgue detectado en AMI. UniqueID: {uniqueid}")
        asyncio.create_task(procesar_transcripcion_post_llamada(uniqueid))

async def main():
    print("🚀 Listener de Transcripción Exclusiva con Vosk Iniciado...")
    await manager.connect()
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())