# 📝 Guía de Mensajes de Commit para PYMEMAD

## 🎯 Estructura del Mensaje

```
<tipo>(<alcance>): <descripción corta>

<descripción larga explicando POR QUÉ>

<footer con referencias>
```

## 📚 Tipos de Commit

### feat - Nueva funcionalidad
```bash
feat(sentry): integrar Sentry para monitoreo de errores

Se agregó Sentry SDK con integraciones para Django, Celery y Redis
para tener visibilidad completa de errores en producción. Esto nos
permitirá detectar y resolver problemas antes de que los usuarios
los reporten.

- Configurado en settings.py con diferentes sample rates por ambiente
- Agregado SENTRY_DSN a los secrets de GitHub
- Integrado con logging existente

Refs: #123
```

### fix - Corrección de bugs
```bash
fix(celery): corregir conexión de Redis usando URL incorrecta

Los workers de Celery estaban conectándose a la instancia antigua
de Redis Cloud en lugar del nuevo servidor. El problema era que los
pods no se reiniciaban después de actualizar los secrets.

- Agregado rollout restart en el workflow de CI/CD
- Creado script manual restart_deployments.sh
- Actualizado README con instrucciones

Fixes: #456
```

### ci - Cambios en CI/CD
```bash
ci(deploy): agregar reinicio automático de pods tras actualizar secrets

Los deployments no reflejaban cambios en variables de entorno sin
un reinicio manual. Ahora el workflow reinicia automáticamente los
pods después de actualizar secrets en Kubernetes.

- Agregado kubectl rollout restart para ambos deployments
- Mejorado manejo de recursos durante deployment
- Agregado notificaciones de Slack en cada etapa
```

### refactor - Refactorización
```bash
refactor(migrations): implementar limpieza automática de migraciones

Siguiendo el patrón de sigescap, ahora limpiamos y recreamos las
migraciones en cada deployment para evitar conflictos y mantener
la base de datos sincronizada con los modelos.

- Creado clear_all_migration.py específico para pymemad
- Actualizado run.sh para incluir limpieza
- Removido collectstatic (se maneja vía S3)
```

### docs - Documentación
```bash
docs(secrets): crear guía completa de GitHub CLI y gestión de secrets

Se documentaron todos los comandos de gh CLI necesarios para el
proyecto y se creó un script automatizado para configurar secrets
desde .env.prod, mejorando la seguridad y facilitando el onboarding.

- Creado GH_CLI_REFERENCE.md con ejemplos
- Script setup_github_secrets.sh para automatización
- Actualizado README con nuevas instrucciones
```

### chore - Tareas de mantenimiento
```bash
chore(docker): actualizar Dockerfile con PostgreSQL 17 y dependencias

Actualizado el Dockerfile siguiendo loginfor para incluir PostgreSQL
client 17 y herramientas adicionales necesarias para el proyecto.

- Agregado wget, curl, gnupg para mayor compatibilidad
- PostgreSQL client actualizado a versión 17
- Mejorado manejo de scripts en /app/scripts
```

### perf - Mejoras de rendimiento
```bash
perf(deploy): remover collectstatic del proceso de deployment

El collectstatic era lento y sobrescribía archivos optimizados en S3.
Se removió del run.sh ya que los estáticos se manejan manualmente
vía AWS S3, reduciendo el tiempo de deployment en ~2 minutos.

- Eliminado collectstatic de run.sh
- Agregado comentario explicativo
- Documentado en README
```

### security - Seguridad
```bash
security(env): remover credenciales hardcodeadas del README

Se detectaron credenciales expuestas en el README. Se movieron todas
las variables sensibles a .env.prod y se creó un sistema seguro de
gestión de secrets con GitHub CLI.

- Credenciales movidas a variables de entorno
- Creado setup_github_secrets.sh
- Agregados archivos sensibles a .gitignore
```

### deps - Dependencias
```bash
deps(monitoring): agregar sentry-sdk con integraciones

Agregado sentry-sdk versión 2.1.0 con integraciones específicas para
Django, Celery y Redis para tener monitoreo completo de errores.

- sentry-sdk[django,celery,redis]~=2.1.0 en requirements.txt
- Configuración en settings.py
- Variables de entorno agregadas
```

### test - Tests
```bash
test(api): agregar tests para endpoints de autenticación

Se agregaron tests unitarios y de integración para los nuevos
endpoints de autenticación con JWT, cubriendo casos de éxito y
manejo de errores.

- Tests para login, logout, refresh token
- Fixtures para usuarios de prueba
- Coverage aumentado al 85%
```

## ❌ Ejemplos de MALOS commits

```bash
# Muy vago
"fix bug"
"update files"
"changes"

# Sin contexto
"actualizar dockerfile"
"agregar script"
"modificar settings"

# Múltiples cambios sin relación
"actualizar dockerfile, agregar sentry, fix redis, cambiar settings"

# Solo describe el QUÉ, no el POR QUÉ
"agregar sentry-sdk a requirements.txt"
```

## ✅ Checklist antes de hacer commit

- [ ] ¿El tipo de commit es correcto?
- [ ] ¿La descripción corta tiene menos de 50 caracteres?
- [ ] ¿Expliqué POR QUÉ hice el cambio, no solo QUÉ cambié?
- [ ] ¿Incluí referencias a issues o tickets si aplica?
- [ ] ¿El mensaje ayudará a entender el cambio en 6 meses?
- [ ] ¿Usé verbos en imperativo (agregar, no agregado)?

## 🚀 Comandos útiles

```bash
# Ver los últimos commits con formato bonito
git log --oneline --graph --decorate -10

# Ver un commit específico con detalles
git show <commit-hash>

# Cambiar el último mensaje de commit (antes de push)
git commit --amend

# Ver plantilla actual
cat .gitmessage

# Hacer commit con la plantilla
git commit  # Se abrirá el editor con la plantilla

# Commit rápido sin plantilla (para cambios triviales)
git commit -m "tipo: descripción corta"
```

## 🔧 Configuración del editor

```bash
# VS Code (recomendado)
git config --global core.editor "code --wait"

# Vim
git config --global core.editor vim

# Nano
git config --global core.editor nano

# Sublime Text
git config --global core.editor "subl -n -w"
```

## 📊 Beneficios de buenos mensajes

1. **Historial útil**: `git log` se vuelve una documentación valiosa
2. **Debugging más fácil**: `git bisect` y `git blame` son más efectivos
3. **Code reviews mejores**: Los reviewers entienden el contexto
4. **Onboarding rápido**: Nuevos desarrolladores entienden decisiones
5. **Generación de CHANGELOG**: Se puede automatizar desde los commits