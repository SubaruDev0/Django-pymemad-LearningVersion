# Guía psql CLI - PostgreSQL

## Conexión al Cluster desde Terminal

```bash
# Conexión básica (reemplazar con tus credenciales)
psql -h [HOST] -U [USUARIO] -d [DATABASE] -p [PUERTO]
```

**Información del Cluster:**
- Host: `a346189-akamai-prod-498459-default.g2a.akamaidb.net`
- Usuario admin: `akmadmin`
- Base de datos por defecto: `defaultdb`
- Puerto: `23667`

## Setup Completo para Nuevo Proyecto

### Paso 1: Generar Contraseña Segura
```bash
# En tu terminal, genera una contraseña segura
PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "Contraseña generada: $PASSWORD"
```

### Paso 2: Conectarse como Admin
```bash
psql -h a346189-akamai-prod-498459-default.g2a.akamaidb.net -U akmadmin -d defaultdb -p 23667
```

### Paso 3: Crear Usuario y Configurarlo

```sql
-- Si el usuario ya existe, primero eliminarlo
DROP USER IF EXISTS pymemad_user;

-- Crear usuario nuevo
-- Reemplazar 'pymemad_user' con tu nombre de usuario
-- Reemplazar 'TU_PASSWORD_SEGURO' con la contraseña generada en Paso 1
CREATE USER pymemad_user WITH PASSWORD 'TU_PASSWORD_SEGURO';

-- Configuración del usuario (UTC-4 para Chile/Venezuela/Bolivia)
ALTER ROLE pymemad_user SET client_encoding TO 'utf8';
ALTER ROLE pymemad_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE pymemad_user SET timezone TO 'UTC-4';
```

### Paso 4: Crear Base de Datos y Asignar Permisos

```sql
-- Crear base de datos con encoding UTF8 y owner específico
CREATE DATABASE pymemad_db WITH ENCODING 'UTF8' OWNER pymemad_user;

-- Otorgar todos los privilegios en la base de datos
GRANT ALL PRIVILEGES ON DATABASE pymemad_db TO pymemad_user;

-- Salir de psql
\q
```

**¿Por qué este orden?**
- **Primero el usuario**: Necesitas que el usuario exista antes de asignarlo como owner
- **UTF8**: Garantiza soporte para todos los caracteres (emojis, acentos, etc.)
- **OWNER al crear**: Define el propietario desde el inicio, evitando problemas de permisos

### Paso 5: Verificar Conexión con Nuevo Usuario
```bash
# Conectarse con el nuevo usuario creado
psql -h a346189-akamai-prod-498459-default.g2a.akamaidb.net -U pymemad_user -d pymemad_db -p 23667
# Ingresa la contraseña generada cuando te la solicite
```

## Ejemplo Completo para Proyecto "pymemad"

```bash
# 1. Terminal: Generar contraseña
PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "Guardar esta contraseña: $PASSWORD"

# 2. Conectarse como admin
psql -h a346189-akamai-prod-498459-default.g2a.akamaidb.net -U akmadmin -d defaultdb -p 23667
```

```sql
-- 3. Dentro de psql: Eliminar usuario si existe y crear nuevo
DROP USER IF EXISTS pymemad_user;
CREATE USER pymemad_user WITH PASSWORD 'cQBlVIYnrOmliKzhjqAOZtemtzLpsMSm';

-- 4. Configurar el usuario
ALTER ROLE pymemad_user SET client_encoding TO 'utf8';
ALTER ROLE pymemad_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE pymemad_user SET timezone TO 'UTC-4';

-- 5. Crear base de datos y asignar permisos
CREATE DATABASE pymemad_db WITH ENCODING 'UTF8' OWNER pymemad_user;
GRANT ALL PRIVILEGES ON DATABASE pymemad_db TO pymemad_user;

-- 6. Verificar creación
\l                    -- Lista bases de datos
\du                   -- Lista usuarios
\q                    -- Salir
```

```bash
# 6. Terminal: Probar conexión con nuevo usuario
psql -h a346189-akamai-prod-498459-default.g2a.akamaidb.net -U pymemad_user -d pymemad_db -p 23667
```

### Gestión de Base de Datos y Schemas

#### Eliminar y Recrear Base de Datos
```sql
-- OPCIÓN 1: Eliminar base de datos completa (requiere desconectar todos los usuarios)
-- Primero terminar todas las conexiones
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'pymemad_db' AND pid <> pg_backend_pid();

-- Luego eliminar la base de datos
DROP DATABASE IF EXISTS pymemad_db;

-- Recrear la base de datos
CREATE DATABASE pymemad_db WITH ENCODING 'UTF8' OWNER pymemad_user;
```

#### Eliminar y Recrear Schema Public (Más común y rápido)
```sql
-- Conectarse a la base de datos específica
\c pymemad_db

-- OPCIÓN 2: Eliminar y recrear solo el schema public (conserva la DB)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Restaurar permisos del schema
GRANT ALL ON SCHEMA public TO pymemad_user;
GRANT ALL ON SCHEMA public TO public;

-- Verificar que está limpio
\dt  -- No debería mostrar tablas
```

#### Limpiar Todo el Contenido sin Eliminar Schema
```sql
-- OPCIÓN 3: Eliminar todas las tablas sin eliminar el schema
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    -- Eliminar todas las tablas
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
```

### Gestión de Usuarios y Permisos
```sql
-- Crear usuario con contraseña
CREATE USER nombre_usuario WITH PASSWORD 'contraseña';

-- Crear usuario con permisos de superusuario
CREATE USER nombre_usuario WITH SUPERUSER PASSWORD 'contraseña';

-- Cambiar contraseña
ALTER USER nombre_usuario WITH PASSWORD 'nueva_contraseña';

-- Otorgar todos los privilegios en una base de datos
GRANT ALL PRIVILEGES ON DATABASE nombre_db TO nombre_usuario;

-- Otorgar permisos específicos
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nombre_usuario;

-- Hacer propietario de una base de datos
ALTER DATABASE nombre_db OWNER TO nombre_usuario;

-- Eliminar usuario (primero revocar permisos)
REVOKE ALL PRIVILEGES ON DATABASE nombre_db FROM nombre_usuario;
DROP USER IF EXISTS nombre_usuario;
```

### Comandos de Navegación en psql
```sql
\l                    -- Listar todas las bases de datos
\c nombre_db          -- Conectarse a una base de datos
\dt                   -- Listar todas las tablas
\d nombre_tabla       -- Describir estructura de una tabla
\du                   -- Listar usuarios y roles
\dn                   -- Listar esquemas
\df                   -- Listar funciones
\dv                   -- Listar vistas
\q                    -- Salir de psql
\?                    -- Ayuda de comandos psql
\h                    -- Ayuda de comandos SQL
```

### Respaldos y Restauración

#### Respaldo (Backup)
```bash
# Respaldar una base de datos completa
pg_dump -h host -U usuario -d nombre_db > backup.sql

# Respaldar con compresión
pg_dump -h host -U usuario -d nombre_db -Fc > backup.dump

# Respaldar solo esquema (sin datos)
pg_dump -h host -U usuario -d nombre_db --schema-only > schema.sql

# Respaldar solo datos (sin esquema)
pg_dump -h host -U usuario -d nombre_db --data-only > data.sql

# Respaldar tabla específica
pg_dump -h host -U usuario -d nombre_db -t nombre_tabla > tabla.sql
```

#### Restauración
```bash
# Restaurar desde archivo SQL
psql -h host -U usuario -d nombre_db < backup.sql

# Restaurar desde archivo comprimido
pg_restore -h host -U usuario -d nombre_db backup.dump

# Restaurar con creación de base de datos
pg_restore -h host -U usuario -C -d postgres backup.dump
```

#### Ejemplo de Respaldo para tu Cluster
```bash
# Backup
pg_dump -h a346189-akamai-prod-498459-default.g2a.akamaidb.net -U akmadmin -p 23667 -d nombre_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar
psql -h a346189-akamai-prod-498459-default.g2a.akamaidb.net -U akmadmin -p 23667 -d nombre_db < backup.sql
```

### Consultas Útiles de Administración
```sql
-- Ver conexiones activas
SELECT pid, usename, datname, client_addr, state 
FROM pg_stat_activity;

-- Ver tamaño de bases de datos
SELECT datname, pg_size_pretty(pg_database_size(datname)) as size 
FROM pg_database;

-- Ver tamaño de tablas
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Terminar conexión específica
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'nombre_db' AND pid <> pg_backend_pid();
```

### Notas Importantes
- Siempre hacer respaldos antes de cambios importantes
- Usar transacciones para operaciones críticas: `BEGIN;` ... `COMMIT;` o `ROLLBACK;`
- El timezone 'UTC-3' corresponde a Argentina/Chile/Uruguay
- Para producción, considerar usar variables de entorno o archivos .pgpass para las contraseñas
