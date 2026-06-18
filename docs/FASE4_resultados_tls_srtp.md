# Fase 4 — Cifrado TLS + SRTP en telefonía SIP
## Control ISO 27001: A.8.24 (Uso de criptografía) · ISO 25010: Seguridad/Confidencialidad

Fecha: 18/06/2026
Evidencia archivada: `evidencia/01_tls_transports.txt`, `evidencia/01_tls_endpoint_1001.txt`

## Configuración aplicada

### Certificado
- Tipo: autofirmado (laboratorio) · Host: 192.168.18.211
- Descripción: cert-tls-telesecure-fase4 · CA generada: 7c761f9a9fe8
- SSL Method: **tlsv1_2** (se rechazan SSLv3/TLS1.0/1.1 por inseguros)

### Transporte TLS (servidor)
```
Transport:  0.0.0.0-tls   tls   3   96   0.0.0.0:5061
```
La PBX escucha señalización SIP cifrada en el puerto **5061/TLS**.

### Extensión 1001 — cifrado FORZADO (evidencia clave)
```
transport                    : 0.0.0.0-tls    <- señalizacion por TLS
media_encryption             : sdes           <- audio cifrado (SRTP)
media_encryption_optimistic  : false          <- SRTP OBLIGATORIO, no opcional
webrtc                       : no
```

## Análisis de auditor

1. **Confidencialidad de la señalización (TLS):** todo el intercambio SIP
   (INVITE, credenciales, números marcados) viaja cifrado por TLS 1.2. Un atacante
   con captura de red (Wireshark) no puede leer la señalización.

2. **Confidencialidad del medio (SRTP):** el audio de la llamada se cifra con SRTP
   (perfil `sdes`). La captura del RTP no permite reconstruir la conversación.

3. **Cifrado obligatorio, no oportunista:** `media_encryption_optimistic = false`
   es el punto crítico de la auditoría. Significa que la extensión **rechaza** medios
   sin cifrar — el cifrado está *forzado*, no meramente *disponible*. Una extensión
   mal configurada que intente RTP plano no establecerá la llamada.

4. **Versión de protocolo segura:** al fijar `tlsv1_2` se descartan versiones
   obsoletas (SSLv3, TLS 1.0/1.1) con vulnerabilidades conocidas (POODLE, BEAST).

## Limitaciones documentadas (honestidad técnica para el informe)
- **Certificado autofirmado:** aceptable en laboratorio; en producción se usaría una
  CA reconocida (Let's Encrypt — la misma pantalla de FreePBX lo soporta).
- **Verify Client/Server = No:** necesario con certificado autofirmado para que los
  softphones conecten. En producción con CA real se activaría la verificación mutua.
- **UDP coexiste en el servidor:** se mantuvo el transporte UDP activo a nivel de PBX
  para no interrumpir extensiones de demostración previas, pero el cifrado se **fuerza
  por extensión** (transport=tls + SRTP obligatorio), que es el control efectivo.

## Conclusión para el informe
TeleSecure cifra la telefonía de extremo a extremo: TLS 1.2 para la señalización y
SRTP obligatorio para el medio, cumpliendo A.8.24. La evidencia (`pjsip show endpoint`)
demuestra cifrado *forzado* a nivel de extensión, no solo disponible — la diferencia
entre "se puede cifrar" y "se debe cifrar" es el núcleo del control.
