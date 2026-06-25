# Fix del audio RTP en Docker/WSL2 — pasos A1 y A2

## Problema confirmado
channelstats muestra 0 paquetes RTP (Rx y Tx). Asterisk (172.20.0.6) anuncia
su IP interna de Docker en el SDP; los softphones de Windows no enrutan a esa IP.

## A1 — Por GUI (probar primero)
Settings > Asterisk SIP Settings > chan_pjsip > transporte udp:
  External IP Address: 127.0.0.1
  Local network:       172.16.0.0/12
Submit > Apply Config > core reload

## A2 — Forzar media address en rtp.conf (si A1 falla)
Ejecutar en PowerShell:

  # 1. Ver el rtp.conf actual
  docker exec telesecure_freepbx cat /etc/asterisk/rtp.conf

  # 2. Forzar que Asterisk publique 127.0.0.1 como media address
  docker exec telesecure_freepbx bash -c "echo 'rtp_start=10000' >> /etc/asterisk/rtp_custom.conf"

## A3 — La solución de fondo (host networking) — NO aplicable en Windows/WSL2
network_mode: host funciona en Linux nativo pero NO en Docker Desktop Windows.
Por eso el audio en este stack es intrínsecamente problemático.
Documentar como limitación de entorno si A1 y A2 no resuelven.
