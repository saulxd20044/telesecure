# Disparador midPoint → Webhook: SOLUCIÓN FINAL (funcionando)

## El problema que costó 8 intentos
En midPoint 4.10, con `generalNotifier` + `bodyExpression` + `customTransport`,
el body generado por el `bodyExpression` NO llegaba al `customTransport`:
`message.getBody()` devolvía vacío (`{}`). Confirmado con log de diagnóstico
en el webhook: `DIAGNOSTICO payload recibido: {}`.

Además, dentro del `bodyExpression`, ningún método exponía el OID del usuario
en un evento de modify (asignar rol a usuario existente):
- event.getRequesteeObject().getOid()  -> vacío
- event.getRequestee().getOid()        -> SimpleObjectRef, sin getFullName
- event.getRequesteeOid()              -> vacío
- event.getFocusContext()...           -> vacío
- requestee (variable suelta)          -> vacío

## La solución (clave doble)
1. **Mover TODA la lógica al script del `customTransport`**, donde la variable
   `event` SÍ está disponible. No depender de que el body fluya del notifier
   al transport.
2. **Usar `event.requestee?.resolveObjectType()`** (patrón oficial Evolveum,
   doc custom-transport). `requestee` es un SimpleObjectRef; hay que llamar
   `resolveObjectType()` para obtener el UserType completo con OID, nombre y email.

## Resultado verificado
```
DIAGNOSTICO payload recibido: {'oid': '213d5bf5-7b73-4d3c-9b0c-8414a7bc5077',
                               'nombre': 'Agente Prueba',
                               'correo': 'agente.prueba@utp.pe'}
```
midPoint procesa la notificación de forma asíncrona (tarda unos segundos),
y el webhook crea la extensión SIP automáticamente.

## El generalNotifier queda solo con el filtro (sin bodyExpression útil);
## el transport hace todo: resuelve el usuario, arma el JSON y hace el POST.
