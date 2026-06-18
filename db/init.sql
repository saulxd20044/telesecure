-- =====================================================================
-- Proyecto TeleSecure — Fase 2
-- Script de inicialización de MariaDB 10.6
--
-- Se ejecuta automáticamente UNA SOLA VEZ en el primer arranque del
-- contenedor (montado en /docker-entrypoint-initdb.d/).
--
-- Estrategia de aislamiento (sin conflictos con FreePBX):
--   * FreePBX es dueño exclusivo de:  `asterisk` y `asteriskcdrdb`
--   * midPoint es dueño exclusivo de: `midpoint` (repositorio interno,
--     sus ~80 tablas las crea midPoint automáticamente al arrancar)
--     y `midpoint_integration` (tablas puente para el aprovisionamiento)
--   * Cada servicio tiene SU PROPIO usuario con permisos SOLO sobre
--     sus bases (mínimo privilegio — ISO 27001 A.5.18). Ningún usuario
--     de aplicación usa root.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) BASES DE DATOS DE FREEPBX
--    Con DB_EMBEDDED=FALSE, FreePBX espera que existan ambas bases
--    y se encarga él mismo de poblar sus tablas. NO crear tablas aquí.
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS asterisk
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS asteriskcdrdb
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Usuario exclusivo de FreePBX: solo sus dos bases, nada más.
CREATE USER IF NOT EXISTS 'fpbx_user'@'%' IDENTIFIED BY 'EWBqM6oAlhXHH0nP81ie';
GRANT ALL PRIVILEGES ON asterisk.*      TO 'fpbx_user'@'%';
GRANT ALL PRIVILEGES ON asteriskcdrdb.* TO 'fpbx_user'@'%';

-- ---------------------------------------------------------------------
-- 2) BASE DE DATOS DEL REPOSITORIO DE midPoint
--    midPoint (4.3, repositorio genérico/Hibernate) crea y migra sus
--    propias tablas (m_user, m_object, m_audit_event, etc.) en el
--    primer arranque. Solo necesita la base vacía y permisos.
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS midpoint
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Usuario exclusivo de midPoint: sin acceso a las bases de FreePBX.
CREATE USER IF NOT EXISTS 'mp_user'@'%' IDENTIFIED BY 'SCKJh78T9K8lekoAaD1e';
GRANT ALL PRIVILEGES ON midpoint.* TO 'mp_user'@'%';

-- ---------------------------------------------------------------------
-- 3) ESQUEMA PUENTE DE INTEGRACIÓN (exclusivo de midPoint)
--    Tablas propias del proyecto para gobernar el aprovisionamiento
--    de extensiones SIP. Viven en una base SEPARADA con prefijo mp_,
--    de modo que es imposible colisionar con las tablas que FreePBX
--    genera en `asterisk`/`asteriskcdrdb`.
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS midpoint_integration
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON midpoint_integration.* TO 'mp_user'@'%';

USE midpoint_integration;

-- Catálogo de roles funcionales de telefonía (asignables desde midPoint)
CREATE TABLE IF NOT EXISTS mp_rol_telefonia (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo          VARCHAR(32)  NOT NULL UNIQUE,        -- AGENTE, SUPERVISOR, ADMIN
    nombre          VARCHAR(100) NOT NULL,
    descripcion     VARCHAR(255),
    permite_ldi     BOOLEAN      NOT NULL DEFAULT FALSE, -- llamadas internacionales
    permite_grabar  BOOLEAN      NOT NULL DEFAULT FALSE,
    creado_en       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Vínculo identidad midPoint <-> extensión SIP en FreePBX
CREATE TABLE IF NOT EXISTS mp_identidad_extension (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    midpoint_oid    CHAR(36)     NOT NULL UNIQUE,        -- OID del usuario en midPoint
    nombre_completo VARCHAR(150) NOT NULL,
    correo          VARCHAR(150),
    extension_sip   VARCHAR(10)  NOT NULL UNIQUE,        -- ej. 1001
    rol_id          INT UNSIGNED NOT NULL,
    estado          ENUM('ACTIVO','SUSPENDIDO','DADO_DE_BAJA')
                                 NOT NULL DEFAULT 'ACTIVO',
    creado_en       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ext_rol FOREIGN KEY (rol_id)
        REFERENCES mp_rol_telefonia(id)
) ENGINE=InnoDB;

-- Bitácora de aprovisionamiento (trazabilidad — ISO 27001 A.8.15)
CREATE TABLE IF NOT EXISTS mp_log_aprovisionamiento (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    midpoint_oid    CHAR(36)     NOT NULL,
    extension_sip   VARCHAR(10),
    operacion       ENUM('ALTA','MODIFICACION','SUSPENSION','BAJA')
                                 NOT NULL,
    resultado       ENUM('EXITO','ERROR','PENDIENTE')
                                 NOT NULL DEFAULT 'PENDIENTE',
    detalle         TEXT,
    ejecutado_por   VARCHAR(100) NOT NULL DEFAULT 'midpoint-connector',
    ejecutado_en    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_log_oid (midpoint_oid),
    INDEX idx_log_fecha (ejecutado_en)
) ENGINE=InnoDB;

-- Datos semilla: catálogo de roles
INSERT INTO mp_rol_telefonia (codigo, nombre, descripcion, permite_ldi, permite_grabar) VALUES
    ('AGENTE',     'Agente de telecomunicaciones', 'Extensión estándar, solo llamadas internas y locales', FALSE, FALSE),
    ('SUPERVISOR', 'Supervisor de piso',           'Monitoreo de llamadas y grabación habilitada',          FALSE, TRUE),
    ('ADMIN',      'Administrador PBX',            'Acceso completo, incluye larga distancia',              TRUE,  TRUE)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

-- ---------------------------------------------------------------------
-- 4) Aplicar permisos
-- ---------------------------------------------------------------------
FLUSH PRIVILEGES;
