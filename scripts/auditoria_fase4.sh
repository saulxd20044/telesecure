#!/usr/bin/env bash
# =====================================================================
# auditoria_fase4.sh — Recolección automática de evidencias (Fase 4)
# Ejecuta Trivy sobre las 4 imágenes de la pila y captura el estado
# TLS de la PBX. Las evidencias quedan en ./evidencia/ con timestamp.
# =====================================================================
set -euo pipefail
FECHA=$(date +%Y%m%d_%H%M)
mkdir -p evidencia

IMAGENES=(
  "tiredofit/freepbx:latest"
  "evolveum/midpoint:4.3"
  "mariadb:10.6"
  "proyecto-f3-webhook:latest"   # ajustar al nombre real de tu imagen
)

echo "== [1/2] Escaneo Trivy (A.8.8) =="
for IMG in "${IMAGENES[@]}"; do
  SALIDA="evidencia/02_trivy_$(echo "$IMG" | tr '/:' '__')_${FECHA}.txt"
  echo "  -> $IMG"
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v trivy_cache:/root/.cache \
    -v "$(pwd)/evidencia:/evidencia" \
    aquasec/trivy:latest image \
    --scanners vuln --severity CRITICAL,HIGH,MEDIUM \
    --output "/${SALIDA}" "$IMG" || echo "  (fallo en $IMG, continuar)"
done

echo "== [2/2] Estado TLS de la PBX (A.8.24) =="
docker exec telesecure_freepbx asterisk -rx "pjsip show transports" \
  > "evidencia/01_tls_transports_${FECHA}.txt" || true

echo "Evidencias generadas en ./evidencia/"
ls -la evidencia/
