# Guía de SeparateDatabaseAndState en Django

## ¿Qué es SeparateDatabaseAndState?

`SeparateDatabaseAndState` es una herramienta avanzada de Django que permite separar lo que Django **cree** que está pasando en el modelo (estado) de lo que **realmente** sucede en la base de datos.

Es útil cuando:
- Hay desincronización entre el estado de Django y la base de datos real
- Necesitas ejecutar SQL personalizado pero mantener el estado de Django sincronizado
- Quieres migrar datos de forma segura con validaciones personalizadas
- Necesitas hacer cambios en la base de datos que ya existen pero Django no lo sabe

## Problema Común: Desincronización

### Escenario típico:
```python
# Modelo Django
class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
```

### Error resultante:
```
ProgrammingError at /
column accounts_user.avatar does not exist
LINE 1: ...user"."created_at", "accounts_user"."updated_at", "accounts_...
```

**Causa**: Django cree que la columna existe (según el modelo), pero la base de datos real no tiene esa columna.

## Solución con SeparateDatabaseAndState

### Estructura básica

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app_name', 'previous_migration'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # 1️⃣ STATE: Lo que Django CREE que existe
            state_operations=[
                # Definir cambios del modelo como Django los espera
            ],

            # 2️⃣ DATABASE: Lo que REALMENTE se ejecuta en PostgreSQL
            database_operations=[
                # SQL real que se ejecutará
            ],
        ),
    ]
```

### Ejemplo completo: Agregar campos de perfil

```python
# apps/accounts/migrations/0002_add_profile_fields.py

from django.db import migrations, models
import apps.accounts.models


class Migration(migrations.Migration):
    """
    Migración usando SeparateDatabaseAndState para agregar campos de perfil.

    Esta migración usa dos pasos:
    1. state_operations: Define los cambios en el modelo Django (lo que Django cree que existe)
    2. database_operations: Define los cambios reales en la base de datos

    Esto permite sincronizar el estado de Django con la realidad de la base de datos
    cuando hay desincronización.
    """

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # Lo que Django CREE que existe (sincronizar el estado del modelo)
                migrations.AddField(
                    model_name='user',
                    name='avatar',
                    field=models.ImageField(
                        blank=True,
                        help_text='Foto de perfil del usuario',
                        null=True,
                        upload_to=apps.accounts.models.upload_to_avatars
                    ),
                ),
                migrations.AddField(
                    model_name='user',
                    name='bio',
                    field=models.TextField(
                        blank=True,
                        help_text='Biografía o descripción personal'
                    ),
                ),
                migrations.AddField(
                    model_name='user',
                    name='phone',
                    field=models.CharField(
                        blank=True,
                        help_text='Número de teléfono de contacto',
                        max_length=20
                    ),
                ),
            ],
            database_operations=[
                # Lo que REALMENTE se ejecuta en la base de datos
                migrations.RunSQL(
                    sql="""
                        DO $
                        BEGIN
                            -- Crear campo 'avatar' si no existe
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name='accounts_user'
                                  AND column_name='avatar'
                            ) THEN
                                ALTER TABLE accounts_user
                                ADD COLUMN avatar VARCHAR(100) NULL;
                                RAISE NOTICE '✅ Campo avatar creado';
                            ELSE
                                RAISE NOTICE '⏭️  Campo avatar ya existe, saltando...';
                            END IF;

                            -- Crear campo 'bio' si no existe
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name='accounts_user'
                                  AND column_name='bio'
                            ) THEN
                                ALTER TABLE accounts_user
                                ADD COLUMN bio TEXT DEFAULT '';
                                RAISE NOTICE '✅ Campo bio creado';
                            ELSE
                                RAISE NOTICE '⏭️  Campo bio ya existe, saltando...';
                            END IF;

                            -- Crear campo 'phone' si no existe
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name='accounts_user'
                                  AND column_name='phone'
                            ) THEN
                                ALTER TABLE accounts_user
                                ADD COLUMN phone VARCHAR(20) DEFAULT '';
                                RAISE NOTICE '✅ Campo phone creado';
                            ELSE
                                RAISE NOTICE '⏭️  Campo phone ya existe, saltando...';
                            END IF;
                        END $;
                    """,
                    reverse_sql="""
                        ALTER TABLE accounts_user DROP COLUMN IF EXISTS avatar;
                        ALTER TABLE accounts_user DROP COLUMN IF EXISTS bio;
                        ALTER TABLE accounts_user DROP COLUMN IF EXISTS phone;
                    """
                ),
            ],
        ),
    ]
```

## Componentes clave

### 1. state_operations (Estado de Django)

Define cómo Django debe entender el modelo después de la migración:

```python
state_operations=[
    migrations.AddField(
        model_name='user',
        name='avatar',
        field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
    ),
]
```

**Importante**: Estos campos deben coincidir exactamente con tu modelo Django.

### 2. database_operations (SQL Real)

Define lo que realmente se ejecuta en PostgreSQL:

```python
database_operations=[
    migrations.RunSQL(
        sql="""
            DO $
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='accounts_user'
                      AND column_name='avatar'
                ) THEN
                    ALTER TABLE accounts_user ADD COLUMN avatar VARCHAR(100) NULL;
                    RAISE NOTICE '✅ Campo avatar creado';
                ELSE
                    RAISE NOTICE '⏭️  Campo avatar ya existe, saltando...';
                END IF;
            END $;
        """,
        reverse_sql="ALTER TABLE accounts_user DROP COLUMN IF EXISTS avatar;"
    ),
]
```

### 3. Bloque DO de PostgreSQL

```sql
DO $
BEGIN
    -- Verificar si la columna existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='table_name'
          AND column_name='column_name'
    ) THEN
        -- Si no existe, crearla
        ALTER TABLE table_name ADD COLUMN column_name TYPE;
        RAISE NOTICE '✅ Campo creado';
    ELSE
        -- Si ya existe, informar
        RAISE NOTICE '⏭️  Campo ya existe, saltando...';
    END IF;
END $;
```

**Ventajas del bloque DO:**
- ✅ Idempotente: puedes ejecutarlo múltiples veces sin error
- ✅ Verifica antes de crear
- ✅ Muestra mensajes informativos durante la migración
- ✅ Más seguro en producción

## Casos de uso

### Caso 1: Sincronizar modelo con base de datos existente

Cuando tienes una base de datos con columnas que Django no conoce:

```python
migrations.SeparateDatabaseAndState(
    state_operations=[
        # Agregar el campo al modelo de Django
        migrations.AddField(model_name='user', name='legacy_id', field=models.IntegerField(null=True)),
    ],
    database_operations=[
        # No hacer nada en la DB porque ya existe
        migrations.RunSQL(
            sql="SELECT 1;",  # Operación vacía
            reverse_sql="SELECT 1;"
        ),
    ],
)
```

### Caso 2: Migración de datos complejos

Cuando necesitas transformar datos durante la migración:

```python
migrations.SeparateDatabaseAndState(
    state_operations=[
        migrations.AddField(model_name='user', name='full_name', field=models.CharField(max_length=200)),
    ],
    database_operations=[
        migrations.RunSQL(
            sql="""
                DO $
                BEGIN
                    -- Crear columna
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='accounts_user' AND column_name='full_name'
                    ) THEN
                        ALTER TABLE accounts_user ADD COLUMN full_name VARCHAR(200);

                        -- Migrar datos existentes
                        UPDATE accounts_user
                        SET full_name = CONCAT(first_name, ' ', last_name)
                        WHERE full_name IS NULL;

                        RAISE NOTICE '✅ Campo full_name creado y poblado';
                    END IF;
                END $;
            """,
            reverse_sql="ALTER TABLE accounts_user DROP COLUMN IF EXISTS full_name;"
        ),
    ],
)
```

### Caso 3: Cambiar tipo de campo con validación

```python
migrations.SeparateDatabaseAndState(
    state_operations=[
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(max_digits=10, decimal_places=2),
        ),
    ],
    database_operations=[
        migrations.RunSQL(
            sql="""
                DO $
                BEGIN
                    -- Validar datos antes de cambiar tipo
                    IF EXISTS (
                        SELECT 1 FROM products_product
                        WHERE price::text !~ '^[0-9]+\.?[0-9]*$'
                    ) THEN
                        RAISE EXCEPTION 'Hay precios inválidos que deben corregirse primero';
                    END IF;

                    -- Cambiar tipo de columna
                    ALTER TABLE products_product
                    ALTER COLUMN price TYPE NUMERIC(10,2)
                    USING price::numeric(10,2);

                    RAISE NOTICE '✅ Tipo de price cambiado a NUMERIC(10,2)';
                END $;
            """,
            reverse_sql="ALTER TABLE products_product ALTER COLUMN price TYPE VARCHAR(50);"
        ),
    ],
)
```

## Verificación de columnas en PostgreSQL

### Verificar si una columna existe:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'accounts_user'
  AND column_name = 'avatar';
```

### Verificar estructura completa de una tabla:

```sql
\d accounts_user
```

O con SQL:

```sql
SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'accounts_user'
ORDER BY ordinal_position;
```

## Comandos útiles de Django

### Crear migración vacía:

```bash
python manage.py makemigrations app_name --empty --name custom_migration_name
```

### Ver estado de migraciones:

```bash
python manage.py showmigrations app_name
```

### Ver SQL que se ejecutará:

```bash
python manage.py sqlmigrate app_name 0002
```

### Aplicar migración específica:

```bash
python manage.py migrate app_name 0002
```

### Revertir migración:

```bash
python manage.py migrate app_name 0001
```

## Mejores prácticas

### ✅ Hacer:

1. **Siempre incluir `reverse_sql`** para poder hacer rollback
2. **Usar bloques DO con verificaciones** para idempotencia
3. **Agregar mensajes RAISE NOTICE** para debugging
4. **Documentar el propósito** de la migración en docstring
5. **Probar en desarrollo** antes de aplicar en producción
6. **Usar IF NOT EXISTS** para evitar errores si se ejecuta múltiples veces

### ❌ Evitar:

1. **No usar SeparateDatabaseAndState** si no es necesario (preferir migraciones normales)
2. **No omitir reverse_sql** (siempre debe ser posible revertir)
3. **No hacer cambios destructivos** sin respaldo
4. **No modificar migraciones** una vez aplicadas en producción
5. **No ejecutar SQL peligroso** sin validaciones previas

## Flujo de trabajo recomendado

### 1. Identificar el problema

```bash
# Error típico
ProgrammingError: column accounts_user.avatar does not exist
```

### 2. Verificar estado de la base de datos

```bash
python manage.py dbshell
\d accounts_user
```

### 3. Crear migración vacía

```bash
python manage.py makemigrations accounts --empty --name add_profile_fields
```

### 4. Implementar SeparateDatabaseAndState

Editar el archivo de migración con `state_operations` y `database_operations`.

### 5. Probar la migración

```bash
# Ver el SQL que se ejecutará
python manage.py sqlmigrate accounts 0002

# Aplicar la migración
python manage.py migrate accounts

# Verificar que funcionó
python manage.py dbshell
\d accounts_user
```

### 6. Verificar en la aplicación

Iniciar el servidor y verificar que el error desapareció.

## Troubleshooting

### Problema: "relation already exists"

**Solución**: Usar `IF NOT EXISTS` en el SQL:

```sql
ALTER TABLE accounts_user ADD COLUMN IF NOT EXISTS avatar VARCHAR(100);
```

O mejor, usar el bloque DO con verificación:

```sql
DO $
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='accounts_user' AND column_name='avatar'
    ) THEN
        ALTER TABLE accounts_user ADD COLUMN avatar VARCHAR(100);
    END IF;
END $;
```

### Problema: "migration already applied"

Si necesitas re-ejecutar una migración:

```bash
# Marcar como no aplicada (fake)
python manage.py migrate app_name 0001 --fake

# Aplicar nuevamente
python manage.py migrate app_name 0002
```

### Problema: El estado y la DB están totalmente desincronizados

**Solución nuclear** (solo en desarrollo):

```bash
# 1. Eliminar todas las migraciones
python clear_all_migration.py

# 2. Eliminar la base de datos
python manage.py dbshell
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

# 3. Recrear migraciones desde cero
python manage.py makemigrations
python manage.py migrate
```

## Referencias

- [Django Documentation - SeparateDatabaseAndState](https://docs.djangoproject.com/en/4.2/ref/migration-operations/#django.db.migrations.operations.SeparateDatabaseAndState)
- [PostgreSQL Information Schema](https://www.postgresql.org/docs/current/information-schema.html)
- [PostgreSQL DO Blocks](https://www.postgresql.org/docs/current/sql-do.html)

## Conclusión

`SeparateDatabaseAndState` es una herramienta poderosa para casos edge donde necesitas control fino sobre las migraciones. Úsala cuando:

- ✅ Hay desincronización entre Django y la base de datos
- ✅ Necesitas ejecutar SQL personalizado complejo
- ✅ Quieres validaciones adicionales durante la migración
- ✅ Necesitas migrar datos de forma controlada

Para casos normales, usa las migraciones estándar de Django con `makemigrations` y `migrate`.
