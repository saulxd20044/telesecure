# Análisis de Cumplimiento Normativo
## TeleSecure · ISO/IEC 27001:2022 + ISO/IEC 25010
> Entregable #4 de la rúbrica: relación componente ↔ cláusula ISO 27001 + métricas ISO 25010.

## A. Cumplimiento ISO/IEC 27001:2022 (controles del Anexo A)

| Componente / Mecanismo | Control ISO 27001 | Cómo se cumple | Evidencia |
|---|---|---|---|
| Redes internas de Docker (`telesecure_net`) | **A.8.20** Seguridad de redes / **A.8.22** Segregación de redes | Los contenedores se comunican en una red bridge privada; solo se publican al host los puertos estrictamente necesarios | docker-compose.yml |
| TLS 1.2 en transporte SIP | **A.8.24** Uso de criptografía | Señalización SIP cifrada (puerto 5061/TLS), SSL Method tlsv1_2 | 01_tls_transports.txt |
| SRTP obligatorio en extensiones | **A.8.24** Uso de criptografía | Audio cifrado (sdes), `media_encryption_optimistic=false` (forzado) | 01_tls_endpoint_1001.txt |
| midPoint (RBAC, rol AgenteCallCenter) | **A.5.15** Control de acceso / **A.5.18** Derechos de acceso | El acceso a la extensión SIP se otorga solo vía asignación de rol; gestión centralizada de identidades | rol XML + demo |
| Autenticación centralizada (midPoint IAM) | **A.5.16** Gestión de identidades / **A.5.17** Información de autenticación | Cambio forzado de contraseñas por defecto; credenciales gestionadas por el IAM | login midPoint |
| Auditoría de sesiones (ma_audit_event) | **A.8.15** Registro de eventos / **A.8.16** Actividades de monitoreo | Cada inicio de sesión queda registrado con timestamp, usuario, IP y resultado | 04_midpoint_logins.txt |
| Usuarios de BD segregados (init.sql) | **A.8.2** Derechos de acceso privilegiado / **A.5.15** Control de acceso | Cuentas de BD separadas por servicio, con permisos mínimos (least privilege) | db/init.sql, grants-fase3.sql |
| Secretos por variables de entorno (.env) | **A.8.24** / **A.5.17** | Tokens y contraseñas fuera del código fuente; `.gitignore` excluye `.env` | .env.example + .gitignore |
| Escaneo de vulnerabilidades (Trivy) | **A.8.8** Gestión de vulnerabilidades técnicas | Las 5 imágenes escaneadas; hallazgos priorizados con plan de tratamiento | 02_trivy_*.txt |
| Webhook con token de autenticación | **A.8.5** Autenticación segura | Cada petición de provisión exige `X-Auth-Token` | webhook_provisioner.py |
| Aislamiento del repositorio midPoint (PostgreSQL propio) | **A.8.9** Gestión de configuración | midPoint usa su propia BD, separada de la de FreePBX | docker-compose.yml |

## B. Cumplimiento ISO/IEC 25010 (características de calidad)

| Característica ISO 25010 | Subcaracterística | Cómo se evidencia | Métrica / Resultado |
|---|---|---|---|
| **Seguridad** | Confidencialidad | TLS + SRTP en telefonía; segregación de red y BD | Cifrado forzado verificado |
| **Seguridad** | Integridad / Responsabilidad | Auditoría de sesiones con no repudio | 9 sesiones trazadas, 0 fallidas |
| **Fiabilidad** | Madurez | Análisis estático del conector (0 bugs) | SonarQube Reliability **A** |
| **Fiabilidad** | Disponibilidad | `restart: unless-stopped`; auto-recuperación de contenedores | 5/5 contenedores healthy |
| **Mantenibilidad** | Modularidad / Analizabilidad | Código del webhook limpio, sin duplicación | SonarQube Maintainability **A**, 0% duplicación |
| **Mantenibilidad** | Capacidad de prueba | 32 pruebas unitarias que corren en el build | Tests verdes en Dockerfile |
| **Compatibilidad** | Interoperabilidad | Integración midPoint↔FreePBX vía API GraphQL estándar; SIP estándar | Provisión automática funcional |
| **Adecuación funcional** | Completitud / Corrección | El sistema cumple el caso de uso: asignar rol → extensión creada | Demo end-to-end |

## C. Flujo de datos (para el diagrama de arquitectura)

```
[Admin asigna rol AgenteCallCenter en midPoint]
                 |
                 v
[midPoint detecta evento -> notificador -> customTransport (Groovy)]
                 |  HTTP POST {oid, nombre, correo} + X-Auth-Token
                 v
[Webhook Flask /provision]  --(API GraphQL OAuth2)-->  [FreePBX 17]
                 |                                          |
                 |                                  crea extensión SIP
                 |                                  (endpoint+aor+auth)
                 v                                          v
[Respuesta 200 + extensión asignada]            [Asterisk: fwconsole reload]
                                                            |
                                                            v
                                          [Softphone se registra por TLS:5061]
                                          [Llamada con audio cifrado SRTP]
```

## Conclusión
TeleSecure cubre los controles de seguridad de ISO 27001 aplicables al alcance
(criptografía, control de acceso, auditoría, segregación, gestión de vulnerabilidades)
y demuestra las características de calidad de ISO 25010 con métricas objetivas
(ratings A de SonarQube, cifrado verificado, auditoría con no repudio). La integración
IAM↔PBX es activa y automática, cumpliendo el criterio de excelencia de la rúbrica.
