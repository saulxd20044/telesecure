-- Fase 3: el webhook (mp_user) inyecta extensiones en la BD de FreePBX.
-- Permisos acotados a DML (sin DDL, sin DROP) sobre la base `asterisk`
-- (mínimo privilegio — ISO 27001 A.5.18).
-- Ejecutar una vez:
--   docker exec -i telesecure_db mariadb -uroot -p < db/grants-fase3.sql
GRANT SELECT, INSERT, UPDATE, DELETE ON asterisk.* TO 'mp_user'@'%';
FLUSH PRIVILEGES;
