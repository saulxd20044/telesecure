# Disparador midPoint 4.10 -> Webhook: instrucciones de inserción

## Bloque A — Asignar perfil permissive al sistema de mensajería
Se inserta DENTRO de la etiqueta <systemConfiguration>, en cualquier punto
de primer nivel (p.ej. justo después de </adminGuiConfiguration> y antes
de <expressions>). Hace que las expresiones de notificación puedan ejecutar
llamadas HTTP.

## Bloque B — La configuración de notificaciones (handler + transport)
Se inserta también a primer nivel dentro de <systemConfiguration>,
justo antes de </systemConfiguration>.
