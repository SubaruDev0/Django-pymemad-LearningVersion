# pymemad - Guía de Deployment

## 🚀 Deployment Manual con Docker y Kubernetes

### 1. **Construir y Subir Imagen Docker (Mac M1 → Kubernetes amd64)**

#### ⚠️ IMPORTANTE para Mac M1/M2 (Apple Silicon):
Tu Mac usa arquitectura ARM64, pero Kubernetes en Linode usa AMD64. Debes construir para la arquitectura correcta:

```bash
# 1. Construir imagen para AMD64 (Kubernetes/Linode)
docker buildx build \
  --platform linux/amd64 \
  -f Dockerfile.pymemad \
  -t yllorca/pymemad:latest \
  --push \
  .

# 2. Verificar que la imagen se subió correctamente
docker pull yllorca/pymemad:latest
docker image inspect yllorca/pymemad:latest | grep Architecture
# Debe mostrar: "Architecture": "amd64"

# Alternativa: Verificar en Docker Hub sin descargar
docker manifest inspect yllorca/pymemad:latest | grep architecture
```

### 2. **Configuración de Kubernetes**

#### **Crear Namespace**
```bash
kubectl apply -f k8s/apps/00_pymemad_ns.yaml
```

#### **Crear Secrets de Aplicación**
```bash
# Crear archivo .env.prod con las variables necesarias
kubectl -n pymemad create secret generic pymemad-prod-env --from-env-file=.env.prod
```

#### **Crear Secret para Docker Registry**
```bash
# Cargar variables desde .env.prod
source .env.prod

# Crear secret con las variables
kubectl create secret docker-registry dhregistrykey \
   --docker-server=https://index.docker.io/v1/ \
   --docker-username="$DOCKERHUB_USERNAME" \
   --docker-password="$DOCKERHUB_TOKEN" \
   --docker-email="tu-email@ejemplo.com" \
   --namespace=pymemad
```

### 3. **Aplicar Manifiestos de Kubernetes**

```bash
# Aplicar todos los manifiestos en orden
kubectl apply -f k8s/apps/

# O uno por uno:
kubectl apply -f k8s/apps/00_pymemad_ns.yaml
kubectl apply -f k8s/apps/01_pymemad_k8s.yaml
kubectl apply -f k8s/apps/02_pymemad-tls-certificate.yaml
kubectl apply -f k8s/apps/03_pymemad_ingress.yaml
kubectl apply -f k8s/apps/05_pymemad_cronjobs.yaml
kubectl apply -f k8s/apps/06_pymemad_networkpolicy.yaml
```

### 4. **Configurar GitHub Actions Secrets**

#### **Script automatizado para configurar secrets desde .env.prod**

Crea un archivo `setup_github_secrets.sh`:

```bash
#!/bin/bash

# Cargar variables desde .env.prod
if [ ! -f .env.prod ]; then
    echo "❌ Error: No se encuentra el archivo .env.prod"
    exit 1
fi

# Exportar variables del archivo .env.prod
set -a
source .env.prod
set +a

REPO="yllorca/pymemad"

echo "🔐 Configurando GitHub Secrets para $REPO desde .env.prod"

# Función para crear secret
create_secret() {
    local name=$1
    local value=$2
    if [ -z "$value" ]; then
        echo "  ⚠️  Saltando $name (vacío)"
    else
        echo "  → Creando $name..."
        gh secret set "$name" --body "$value" --repo "$REPO"
    fi
}

# Docker Hub
create_secret "DOCKERHUB_USERNAME" "$DOCKERHUB_USERNAME"
create_secret "DOCKERHUB_TOKEN" "$DOCKERHUB_TOKEN"

# Database
create_secret "POSTGRES_USER" "$POSTGRES_USER"
create_secret "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
create_secret "POSTGRES_HOST" "$POSTGRES_HOST"
create_secret "POSTGRES_PORT" "$POSTGRES_PORT"
create_secret "POSTGRES_DB" "$POSTGRES_DB"

# AWS
create_secret "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID"
create_secret "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET_ACCESS_KEY"
create_secret "AWS_REGION" "$AWS_REGION"
create_secret "AWS_BUCKET" "$AWS_BUCKET"

# Redis
create_secret "REDIS_BASE_URL" "$REDIS_BASE_URL"

# Django
create_secret "SECRET_KEY" "$SECRET_KEY"
create_secret "DEBUG" "$DEBUG"
create_secret "ALLOWED_HOSTS" "$ALLOWED_HOSTS"

# APIs
create_secret "OPENAI_API_KEY" "$OPENAI_API_KEY"
create_secret "DEEPSEEK_API_KEY" "$DEEPSEEK_API_KEY"
create_secret "DEEPSEEK_API_URL" "$DEEPSEEK_API_URL"

# Sentry
create_secret "SENTRY_DSN" "$SENTRY_DSN"
create_secret "ENVIRONMENT" "$ENVIRONMENT"

# Slack (si está configurado)
if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
    create_secret "SLACK_WEBHOOK_URL" "$SLACK_WEBHOOK_URL"
fi

# Kubeconfig (desde archivo)
if [ -f ~/.kube/config ]; then
    echo "  → Creando KUBECONFIG desde archivo..."
    gh secret set KUBECONFIG < ~/.kube/config --repo "$REPO"
else
    echo "  ⚠️  No se encontró ~/.kube/config"
fi

echo ""
echo "✅ Configuración completada!"
echo ""
echo "📋 Lista de secrets creados:"
gh secret list --repo "$REPO"
```

#### **Uso del script**

```bash
# 1. Asegúrate de tener el archivo .env.prod con todas las variables
cp .env.prod.example .env.prod
# Editar .env.prod con tus valores reales

# 2. Hacer el script ejecutable
chmod +x setup_github_secrets.sh

# 3. Ejecutar el script
./setup_github_secrets.sh
```

#### **Comandos individuales (usando variables de entorno)**

Si prefieres configurar los secrets manualmente uno por uno:

```bash
# Primero cargar las variables desde .env.prod
source .env.prod

# Luego usar las variables para crear los secrets
gh secret set DOCKERHUB_USERNAME --body "$DOCKERHUB_USERNAME" --repo yllorca/pymemad
gh secret set DOCKERHUB_TOKEN --body "$DOCKERHUB_TOKEN" --repo yllorca/pymemad
gh secret set POSTGRES_USER --body "$POSTGRES_USER" --repo yllorca/pymemad
gh secret set POSTGRES_PASSWORD --body "$POSTGRES_PASSWORD" --repo yllorca/pymemad
gh secret set POSTGRES_HOST --body "$POSTGRES_HOST" --repo yllorca/pymemad
gh secret set POSTGRES_PORT --body "$POSTGRES_PORT" --repo yllorca/pymemad
gh secret set POSTGRES_DB --body "$POSTGRES_DB" --repo yllorca/pymemad
gh secret set AWS_ACCESS_KEY_ID --body "$AWS_ACCESS_KEY_ID" --repo yllorca/pymemad
gh secret set AWS_SECRET_ACCESS_KEY --body "$AWS_SECRET_ACCESS_KEY" --repo yllorca/pymemad
gh secret set AWS_REGION --body "$AWS_REGION" --repo yllorca/pymemad
gh secret set AWS_BUCKET --body "$AWS_BUCKET" --repo yllorca/pymemad
gh secret set REDIS_BASE_URL --body "$REDIS_BASE_URL" --repo yllorca/pymemad
gh secret set SECRET_KEY --body "$SECRET_KEY" --repo yllorca/pymemad
gh secret set DEBUG --body "$DEBUG" --repo yllorca/pymemad
gh secret set ALLOWED_HOSTS --body "$ALLOWED_HOSTS" --repo yllorca/pymemad
gh secret set OPENAI_API_KEY --body "$OPENAI_API_KEY" --repo yllorca/pymemad
gh secret set DEEPSEEK_API_KEY --body "$DEEPSEEK_API_KEY" --repo yllorca/pymemad
gh secret set DEEPSEEK_API_URL --body "$DEEPSEEK_API_URL" --repo yllorca/pymemad
gh secret set SENTRY_DSN --body "$SENTRY_DSN" --repo yllorca/pymemad
gh secret set ENVIRONMENT --body "$ENVIRONMENT" --repo yllorca/pymemad
gh secret set SLACK_WEBHOOK_URL --body "$SLACK_WEBHOOK_URL" --repo yllorca/pymemad

# KUBECONFIG desde archivo
gh secret set KUBECONFIG < ~/.kube/config --repo yllorca/pymemad
```

#### **Verificar secrets existentes**

```bash
# Listar todos los secrets
gh secret list --repo yllorca/pymemad

# Verificar secrets específicos
gh secret list --repo yllorca/pymemad | grep -E "SENTRY|SLACK|REDIS"
```

#### **Actualizar un secret existente**

```bash
# Ejemplo: actualizar REDIS_BASE_URL
gh secret set REDIS_BASE_URL --body "redis://:nueva_password@nuevo_host:6379/0" --repo yllorca/pymemad
```

#### **Eliminar un secret**

```bash
# Ejemplo: eliminar un secret no usado
gh secret remove UNUSED_SECRET --repo yllorca/pymemad
```

### 5. **Referencia de Comandos GitHub CLI (gh)**

#### **🔐 Gestión de Secrets**

```bash
# Listar todos los secrets
gh secret list --repo yllorca/pymemad

# Crear/actualizar un secret
gh secret set SECRET_NAME --body "valor_secreto" --repo yllorca/pymemad

# Crear secret desde archivo
gh secret set SECRET_NAME < archivo.txt --repo yllorca/pymemad

# Eliminar un secret
gh secret remove SECRET_NAME --repo yllorca/pymemad

# Eliminar múltiples secrets (excepto algunos)
gh secret list --repo yllorca/pymemad | \
  grep -v "KEEP_THIS\|AND_THIS" | \
  awk '{print $1}' | \
  xargs -I {} gh secret remove {} --repo yllorca/pymemad
```

#### **📦 Gestión de Repositorios**

```bash
# Clonar un repositorio
gh repo clone yllorca/pymemad

# Ver información del repositorio
gh repo view yllorca/pymemad --web

# Crear un fork
gh repo fork yllorca/pymemad

# Listar repositorios propios
gh repo list yllorca --limit 10
```

#### **🔄 Pull Requests**

```bash
# Listar PRs abiertos
gh pr list --repo yllorca/pymemad

# Crear un PR
gh pr create --title "Mi PR" --body "Descripción del PR"

# Ver detalles de un PR
gh pr view 123 --repo yllorca/pymemad

# Checkout de un PR
gh pr checkout 123

# Aprobar un PR
gh pr review --approve 123

# Mergear un PR
gh pr merge 123 --squash
```

#### **🏃 GitHub Actions**

```bash
# Ver workflows
gh workflow list --repo yllorca/pymemad

# Ver runs recientes
gh run list --repo yllorca/pymemad --limit 5

# Ver detalles de un run
gh run view 1234567890 --repo yllorca/pymemad

# Re-ejecutar un workflow fallido
gh run rerun 1234567890

# Ver logs de un run
gh run view 1234567890 --log

# Descargar artifacts
gh run download 1234567890 --repo yllorca/pymemad

# Cancelar un workflow en ejecución
gh run cancel 1234567890
```

#### **🐛 Issues**

```bash
# Listar issues
gh issue list --repo yllorca/pymemad

# Crear un issue
gh issue create --title "Bug encontrado" --body "Descripción del bug"

# Ver un issue
gh issue view 123 --repo yllorca/pymemad

# Cerrar un issue
gh issue close 123

# Reabrir un issue
gh issue reopen 123

# Comentar en un issue
gh issue comment 123 --body "Mi comentario"
```

#### **📋 Releases**

```bash
# Listar releases
gh release list --repo yllorca/pymemad

# Crear un release
gh release create v1.0.0 --title "Version 1.0.0" --notes "Notas del release"

# Descargar assets de un release
gh release download v1.0.0 --repo yllorca/pymemad

# Eliminar un release
gh release delete v1.0.0 --yes
```

#### **🔧 Configuración y Auth**

```bash
# Ver estado de autenticación
gh auth status

# Login interactivo
gh auth login

# Login con token
echo $GITHUB_TOKEN | gh auth login --with-token

# Logout
gh auth logout

# Cambiar protocolo de git (https/ssh)
gh config set git_protocol ssh

# Ver configuración actual
gh config list
```

#### **📊 API y Consultas Avanzadas**

```bash
# Hacer una consulta a la API de GitHub
gh api repos/yllorca/pymemad

# Obtener información específica con jq
gh api repos/yllorca/pymemad | jq '.stargazers_count'

# Listar todos los secrets (solo nombres)
gh api repos/yllorca/pymemad/actions/secrets | jq '.secrets[].name'

# Obtener estadísticas del repo
gh api repos/yllorca/pymemad/stats/contributors

# GraphQL query personalizada
gh api graphql -f query='
  query {
    repository(owner:"yllorca", name:"pymemad") {
      stargazerCount
      forkCount
    }
  }'
```

#### **🎯 Comandos Útiles para CI/CD**

```bash
# Ver el último deployment
gh run list --workflow=update-deploy.yaml --limit 1

# Monitorear un workflow en tiempo real
gh run watch

# Verificar estado de todos los workflows
gh workflow list --all

# Habilitar/deshabilitar un workflow
gh workflow enable "workflow-name"
gh workflow disable "workflow-name"

# Ejecutar workflow manualmente
gh workflow run django-test.yaml

# Ver secrets usados en workflows
gh secret list --repo yllorca/pymemad | grep -E "DOCKERHUB|KUBECONFIG|SENTRY"
```

#### **💡 Tips y Trucos**

```bash
# Alias útiles (agregar a ~/.zshrc o ~/.bashrc)
alias ghsl='gh secret list --repo yllorca/pymemad'
alias ghss='gh secret set --repo yllorca/pymemad'
alias ghsr='gh secret remove --repo yllorca/pymemad'
alias ghrl='gh run list --repo yllorca/pymemad --limit 5'
alias ghwl='gh workflow list --repo yllorca/pymemad'

# Ver todos los comandos disponibles
gh --help

# Ver ayuda de un comando específico
gh secret --help

# Actualizar gh CLI
brew upgrade gh  # macOS
sudo apt-get update && sudo apt-get upgrade gh  # Linux
```

## 🔄 CI/CD Automático

El deployment automático se ejecuta al hacer push a `main`:
```bash
git push origin main
```

El workflow de GitHub Actions:
1. Ejecuta tests
2. Construye y sube imagen Docker
3. Actualiza deployments en Kubernetes
4. Maneja recursos limitados automáticamente

## 📊 Monitoreo y Operaciones

### Durante el Deployment

1. **Monitorear logs en tiempo real**:
```bash
kubectl logs -f deployment/pymemad-deployment -n pymemad
```

2. **Ver estado de pods**:
```bash
watch kubectl get pods -n pymemad
```

3. **Verificar recursos utilizados**:
```bash
kubectl describe resourcequota pymemad-quota -n pymemad
```

### Después del Deployment

#### **Verificar Health Checks**:
```bash
# Health check endpoint
curl https://www.pymemad.cl/health/

# Readiness check
curl https://www.pymemad.cl/ready/
```

#### **Gestión de Cache Redis**:
```bash
# Ver estadísticas de cache
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py clear_cache --stats

# Limpiar cache completo (con confirmación)
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py clear_cache

# Limpiar cache sin confirmación
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py clear_cache --force

# Limpiar solo cache del blog
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py clear_cache --type blog

# Limpiar por patrón específico
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py clear_cache --pattern "post_*"

# Ver qué se limpiaría (dry-run)
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py clear_cache --dry-run
```

#### **Monitoreo de Logs**:
```bash
# Logs del deployment principal
kubectl logs deployment/pymemad-deployment -n pymemad --tail=100 -f

# Logs de Celery
kubectl logs deployment/celery-unified-worker -n pymemad --tail=100 -f

# Logs de todos los pods
kubectl logs -n pymemad --all-containers=true --follow
```

#### **Ejecutar Comandos Django**:
```bash
# Crear superusuario
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py createsuperuser

# Ejecutar migraciones
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py migrate

# Collectstatic
kubectl exec -it deployment/pymemad-deployment -n pymemad -- python manage.py collectstatic --noinput
```

## 🛠️ Troubleshooting

### Pods en CrashLoopBackOff
```bash
# Ver logs del pod problemático
kubectl logs <pod-name> -n pymemad --previous

# Describir el pod para más detalles
kubectl describe pod <pod-name> -n pymemad
```

### Problemas de Recursos
```bash
# Ver uso actual
kubectl top pods -n pymemad

# Escalar manualmente si es necesario
kubectl scale deployment/pymemad-deployment --replicas=2 -n pymemad
```

### Rollback de Deployment
```bash
# Ver historial de deployments
kubectl rollout history deployment/pymemad-deployment -n pymemad

# Rollback al deployment anterior
kubectl rollout undo deployment/pymemad-deployment -n pymemad

# Rollback a una versión específica
kubectl rollout undo deployment/pymemad-deployment -n pymemad --to-revision=2
```

## 📊 Script de Monitoreo Completo

### Instalación y Uso

El proyecto incluye un script de monitoreo completo (`monitoring_pymemad.sh`) que proporciona una vista integral del estado del cluster.

#### **Ejecutar el script:**
```bash
# Hacer ejecutable (solo primera vez)
chmod +x monitoring_pymemad.sh

# Ejecutar monitoreo completo
./monitoring_pymemad.sh

# Monitoreo continuo cada 30 segundos
watch -n 30 ./monitoring_pymemad.sh

# Guardar reporte con timestamp
./monitoring_pymemad.sh > reporte_$(date +%Y%m%d_%H%M%S).txt

# Ejecutar remotamente en el cluster
kubectl exec -it deployment/pymemad-deployment -n pymemad -- bash -c "$(cat monitoring_pymemad.sh)"
```

#### **Información que proporciona:**
- 📊 **Estado de pods** - Running, Pending, Failed
- 💾 **Uso de recursos** - CPU y memoria por pod
- 🚀 **Estado de deployments** - Replicas ready/desired
- 📏 **ResourceQuota** - Uso vs límites del namespace
- ⚖️ **HPA Status** - Auto-scaling metrics
- 🌐 **Servicios y endpoints** - IPs y conectividad
- 📅 **Eventos recientes** - Últimos 10 eventos del namespace
- ⚠️ **Errores en logs** - Detección de errores en últimas 2 horas
- 🔄 **Estado de Celery** - Beat y workers status
- 🏥 **Health checks** - Verificación de endpoints /health/ y /ready/
- 📋 **Resumen de salud** - Estado general del cluster
- 💡 **Recomendaciones** - Sugerencias automáticas basadas en métricas

#### **Ejemplo de salida:**
```
=========================================
    MONITOREO DEL CLUSTER pymemad
    Fri Dec 22 10:30:45 UTC 2023
=========================================

📊 ESTADO DE PODS:
===================
NAME                                    READY   STATUS    RESTARTS   AGE
pymemad-deployment-7b9f5d4-x2k9m      1/1     Running   0          2d
pymemad-deployment-7b9f5d4-z8n3p      1/1     Running   0          2d
celery-unified-worker-6d5f8c9-m4k2l    1/1     Running   0          5d

💾 USO DE RECURSOS POR POD:
============================
NAME                                    CPU(cores)   MEMORY(bytes)
pymemad-deployment-7b9f5d4-x2k9m      45m          180Mi
pymemad-deployment-7b9f5d4-z8n3p      48m          185Mi
celery-unified-worker-6d5f8c9-m4k2l    120m         350Mi

📏 RESOURCEQUOTA STATUS:
========================
Resource         Used    Hard
--------         ----    ----
requests.cpu     258m    400m
requests.memory  715Mi   1Gi

✅ Todos los pods están saludables
```

### Alertas y Notificaciones

El script detecta automáticamente condiciones críticas:
- CPU usage > 80%
- Pods en CrashLoopBackOff
- Servicios sin endpoints
- Celery Beat no funcionando
- Health checks fallando

## 🔄 Actualización de Secrets en Kubernetes

### Reinicio Manual de Deployments

Cuando actualizas secrets en GitHub pero no hay cambios de código, los pods no se reinician automáticamente. Usa el script `restart_deployments.sh` para aplicar los nuevos secrets:

#### **Instalación y Uso:**
```bash
# Hacer ejecutable (solo primera vez)
chmod +x restart_deployments.sh

# Ejecutar el script
./restart_deployments.sh
```

#### **¿Qué hace el script?**
1. Verifica la configuración de kubectl
2. Muestra el estado actual de los deployments
3. Lista los secrets disponibles
4. Pide confirmación antes de proceder
5. Reinicia ambos deployments:
   - `celery-unified-worker`
   - `pymemad-deployment`
6. Espera a que los rollouts terminen
7. Verifica las nuevas variables de entorno
8. Muestra el estado final de los pods

#### **Ejemplo de uso:**
```bash
$ ./restart_deployments.sh

==================================================
    PYMEMAD - Reinicio de Deployments
==================================================

📝 Estado actual de los deployments:
-----------------------------------
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
celery-unified-worker   1/1     1            1           15d
pymemad-deployment      2/2     2            2           15d

📦 Verificando secrets actuales:
--------------------------------
AWS_ACCESS_KEY_ID
AWS_BUCKET
AWS_REGION
AWS_SECRET_ACCESS_KEY
DEBUG
... y más secrets

¿Deseas reiniciar los deployments para aplicar los nuevos secrets? (s/n): s

🔄 Reiniciando deployments...
----------------------------
→ Reiniciando celery-unified-worker...
  ⏳ Esperando que termine el rollout...
  ✅ celery-unified-worker reiniciado exitosamente

→ Reiniciando pymemad-deployment...
  ⏳ Esperando que termine el rollout...
  ✅ pymemad-deployment reiniciado exitosamente

📊 Estado final de los pods:
---------------------------
NAME                                     READY   STATUS    RESTARTS   AGE
celery-unified-worker-6d4c9f7b6-x2mj9   1/1     Running   0          30s
pymemad-deployment-5b7d8c9f4-j8k2m      1/1     Running   0          25s
pymemad-deployment-5b7d8c9f4-n9p3l      1/1     Running   0          15s

🔍 Verificando variables de entorno en Celery (REDIS_BASE_URL):
--------------------------------------------------------------
REDIS_BASE_URL=redis://:ioJuc9...@45.79.197.72:6379/8

✅ Proceso completado
```

#### **¿Cuándo usar este script?**
- Después de actualizar secrets en GitHub con `gh secret set`
- Cuando cambias variables de entorno sin modificar código
- Si los pods están usando valores antiguos de configuración
- Para forzar la recarga de secrets sin hacer un deployment completo

#### **Reinicio Automático en CI/CD**
El workflow de GitHub Actions (`update-deploy.yaml`) ahora incluye reinicio automático de pods después de actualizar secrets. Esto ocurre automáticamente cuando:
1. Haces push a la rama `main`
2. El workflow actualiza los secrets en Kubernetes
3. Ejecuta `kubectl rollout restart` para ambos deployments
4. Los pods se reinician con las nuevas variables de entorno

**Nota:** Si solo actualizas secrets sin hacer push a main, debes usar el script manual `restart_deployments.sh`.
