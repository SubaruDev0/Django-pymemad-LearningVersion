# 📚 Guía de Trabajo para Practicante - PyMemad

## 🎯 Información General

**Repositorio:** https://github.com/Hello-World-SpA/pymemad
**Tu Usuario:** SubaruDev0
**Rol:** Colaborador con permisos de escritura (write)
**Mentor:** @yllorca

---

## 🚀 Configuración Inicial

### 1. Aceptar la Invitación
- Revisa tu email asociado a GitHub
- Acepta la invitación al repositorio `Hello-World-SpA/pymemad`
- Verifica que tienes acceso en: https://github.com/Hello-World-SpA/pymemad

### 2. Configurar Git Localmente
```bash
# Configurar tu nombre y email
git config --global user.name "Tu Nombre"
git config --global user.email "subaru0.dev@gmail.com"

# Configurar editor preferido (opcional)
git config --global core.editor "code --wait"  # Para VS Code
```

### 3. Clonar el Repositorio
```bash
# Usando SSH (recomendado)
git clone git@github.com:Hello-World-SpA/pymemad.git

# O usando HTTPS
git clone https://github.com/Hello-World-SpA/pymemad.git

# Entrar al directorio
cd pymemad
```

### 4. Configurar el Entorno de Desarrollo

#### Crear entorno virtual
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En Mac/Linux:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

#### Instalar dependencias
```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# Crear archivo .env para desarrollo local
cp .env.example .env  # Solicita los valores a @yllorca
```

---

## 📋 Flujo de Trabajo (IMPORTANTE)

### ⚠️ REGLA PRINCIPAL: NUNCA hagas push directo a `main`

El repositorio está protegido y NO permite push directo a la rama principal. TODO cambio debe hacerse mediante Pull Request.

### 📝 Proceso Paso a Paso

#### 1. Actualizar tu rama main local
```bash
# Asegúrate de estar en main
git checkout main

# Actualizar con los últimos cambios
git pull origin main
```

#### 2. Crear una nueva rama para tu tarea
```bash
# Nomenclatura de ramas:
# - feature/nombre-funcionalidad  (para nuevas características)
# - fix/nombre-bug                (para corrección de errores)
# - refactor/nombre-cambio        (para refactorización)
# - docs/nombre-documento         (para documentación)

# Ejemplo:
git checkout -b feature/agregar-validacion-email
```

#### 3. Hacer tus cambios
```bash
# Edita los archivos necesarios
# Prueba tu código localmente

# Ver estado de cambios
git status

# Ver diferencias
git diff
```

#### 4. Commit de cambios
```bash
# Agregar archivos al staging
git add .  # O específicos: git add archivo1.py archivo2.py

# Hacer commit con mensaje descriptivo
git commit -m "feat: agregar validación de email en formulario de contacto"
```

**Formato de mensajes de commit:**
- `feat:` Nueva funcionalidad
- `fix:` Corrección de bug
- `docs:` Cambios en documentación
- `style:` Cambios de formato (que no afectan funcionalidad)
- `refactor:` Refactorización de código
- `test:` Agregar o modificar tests
- `chore:` Tareas de mantenimiento

#### 5. Push a tu rama
```bash
# Primera vez en la rama
git push -u origin feature/agregar-validacion-email

# Siguientes veces
git push
```

#### 6. Crear Pull Request

**Opción A: Usando GitHub CLI (Recomendado)**
```bash
# Instalar GitHub CLI si no lo tienes
# Mac: brew install gh
# Linux: Ver https://github.com/cli/cli/blob/trunk/docs/install_linux.md
# Windows: winget install --id GitHub.cli

# Autenticarse (solo la primera vez)
gh auth login

# Crear PR desde la terminal
gh pr create \
  --title "feat: agregar validación de email" \
  --body "## Descripción
  - Agregada validación de formato de email
  - Previene envío de formularios con emails inválidos

  ## Testing
  - Probado con emails válidos e inválidos
  - Todos los tests pasan" \
  --assignee yllorca \
  --reviewer yllorca

# O usar modo interactivo (más fácil)
gh pr create
# Te preguntará título, descripción, etc.
```

**Opción B: Usando la interfaz web**
1. Ve a: https://github.com/Hello-World-SpA/pymemad
2. Verás un botón amarillo: "Compare & pull request"
3. O ve a la pestaña "Pull requests" → "New pull request"
4. Completa:
   - **Título:** Descripción breve del cambio
   - **Descripción:**
     - Qué cambiaste
     - Por qué lo cambiaste
     - Cómo probarlo
     - Screenshots si aplica
5. Asigna a @yllorca como reviewer
6. Click en "Create pull request"

#### 7. Proceso de Revisión
- Espera la revisión de @yllorca
- Si hay comentarios o cambios solicitados:
  ```bash
  # En tu rama local
  git add archivos_modificados
  git commit -m "fix: aplicar cambios solicitados en PR"
  git push
  ```
- Una vez aprobado, @yllorca hará el merge

---

## 🔧 GitHub CLI - Comandos Útiles

### Instalación y Configuración
```bash
# Instalar (solo una vez)
# Mac
brew install gh

# Linux (Debian/Ubuntu)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Windows
winget install --id GitHub.cli

# Autenticarse (solo la primera vez)
gh auth login
```

### Trabajando con PRs
```bash
# Crear PR
gh pr create                          # Modo interactivo
gh pr create --title "Mi PR" --body "Descripción"

# Ver PRs
gh pr list                            # Lista todos los PRs
gh pr view                            # Ver PR actual
gh pr view 123                        # Ver PR específico

# Revisar cambios
gh pr diff                            # Ver diff del PR actual
gh pr checkout 123                    # Cambiar a la rama del PR #123

# Comentar en PR
gh pr comment 123 --body "Buen trabajo!"

# Ver estado de checks/CI
gh pr checks                          # Ver estado de CI/CD
```

### Trabajando con Issues
```bash
# Listar issues
gh issue list
gh issue list --assignee @me          # Mis issues

# Ver issue
gh issue view 45

# Crear issue
gh issue create                       # Modo interactivo
gh issue create --title "Bug" --body "Descripción del bug"

# Comentar
gh issue comment 45 --body "Trabajando en esto"
```

### Información del Repo
```bash
# Ver información del repo
gh repo view

# Clonar repo
gh repo clone Hello-World-SpA/pymemad

# Ver workflows/CI
gh workflow list
gh run list                           # Ver ejecuciones recientes
gh run watch                          # Ver ejecución en tiempo real
```

## 🔄 Comandos Git Más Usados

### Básicos
```bash
git status                  # Ver estado actual
git log --oneline          # Ver historial de commits
git diff                   # Ver cambios no commiteados
git diff --staged          # Ver cambios en staging
```

### Ramas
```bash
git branch                 # Ver ramas locales
git branch -a              # Ver todas las ramas (locales y remotas)
git checkout rama         # Cambiar de rama
git checkout -b nueva-rama # Crear y cambiar a nueva rama
git branch -d rama        # Eliminar rama local (ya mergeada)
git branch -D rama        # Forzar eliminación de rama local
```

### Actualizar y Sincronizar
```bash
git fetch                  # Traer cambios del remoto sin aplicar
git pull                   # Traer y aplicar cambios
git pull origin main       # Actualizar main específicamente
```

### Deshacer Cambios
```bash
git checkout -- archivo    # Deshacer cambios en archivo no staged
git reset HEAD archivo     # Quitar archivo del staging
git reset --soft HEAD~1    # Deshacer último commit (mantiene cambios)
git reset --hard HEAD~1    # Deshacer último commit (PIERDE cambios)
```

---

## 🏗️ Estructura del Proyecto

```
pymemad/
├── apps/                  # Aplicaciones Django
│   ├── accounts/         # Gestión de usuarios
│   ├── core/            # Funcionalidad principal
│   ├── landing/         # Páginas públicas
│   ├── news/            # Gestión de noticias
│   ├── panel/           # Panel de administración
│   └── ...
├── pymemadweb/           # Configuración Django
│   ├── settings.py      # ⚠️ NO MODIFICAR sin consultar
│   └── urls.py
├── templates/            # Plantillas HTML
├── static/              # Archivos estáticos (CSS, JS, imágenes)
├── scripts/             # Scripts de utilidad
├── requirements.txt     # Dependencias Python
└── manage.py           # Comando principal Django
```

---

## 🧪 Testing

### Ejecutar tests
```bash
# Todos los tests
python manage.py test

# Tests de una app específica
python manage.py test apps.core

# Con más detalle
python manage.py test --verbosity=2
```

### Antes de hacer Push
- [ ] Tu código funciona localmente
- [ ] Los tests pasan
- [ ] No hay errores de sintaxis
- [ ] Has probado los cambios manualmente
- [ ] El código sigue los estándares del proyecto

---

## 🚨 Reglas Importantes

### ✅ HACER
- Crear PR para TODOS los cambios
- Escribir commits descriptivos
- Probar tu código antes de hacer push
- Preguntar si tienes dudas
- Documentar funciones complejas
- Seguir los patrones existentes en el código

### ❌ NO HACER
- Push directo a `main` (está bloqueado)
- Commits con mensajes como "fix", "cambios", "update"
- Modificar archivos de configuración sin consultar
- Subir archivos `.env` o secrets
- Hacer force push (`git push -f`)
- Trabajar directamente en `main`

---

## 📞 Comunicación

### Cuando necesites ayuda:
1. **Revisa esta guía** primero
2. **Busca en el código** ejemplos similares
3. **Pregunta en el PR** si es sobre código específico
4. **Contacta a @yllorca** para dudas generales

### Reportar problemas:
- Crea un issue en GitHub con:
  - Descripción clara del problema
  - Pasos para reproducirlo
  - Comportamiento esperado vs actual
  - Screenshots si aplica

---

## 🎓 Recursos de Aprendizaje

### Django
- [Documentación oficial Django](https://docs.djangoproject.com/)
- [Django Girls Tutorial](https://tutorial.djangogirls.org/)
- [MDN Django Tutorial](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django)

### Git
- [Pro Git Book (Español)](https://git-scm.com/book/es/v2)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Atlassian Git Tutorial](https://www.atlassian.com/git/tutorials)

### Python
- [Python oficial](https://docs.python.org/3/)
- [Real Python](https://realpython.com/)
- [Python PEP 8 - Guía de estilo](https://www.python.org/dev/peps/pep-0008/)

---

## 💡 Tips para el Éxito

1. **Commits frecuentes**: Mejor muchos commits pequeños que uno gigante
2. **Pull frecuente**: Actualiza tu rama `main` diariamente
3. **PR pequeños**: Más fáciles de revisar y aprobar
4. **Prueba todo**: Si modificas algo, pruébalo
5. **Lee el código existente**: Aprende de los patrones ya implementados
6. **Pregunta**: Mejor preguntar que asumir

---

## 🆘 Solución de Problemas Comunes

### "Permission denied" al hacer push
```bash
# Verifica que estás en tu rama, no en main
git branch  # Debe mostrar tu rama con *

# Si estás en main por error
git checkout -b feature/mi-cambio
git push -u origin feature/mi-cambio
```

### Conflictos al hacer pull
```bash
# Actualiza tu rama con main
git checkout main
git pull
git checkout tu-rama
git merge main
# Resuelve conflictos si los hay
git add .
git commit -m "fix: resolver conflictos con main"
git push
```

### Cambios accidentales en main
```bash
# Si no has hecho commit
git stash  # Guarda cambios temporalmente
git checkout -b feature/nueva-rama
git stash pop  # Recupera los cambios

# Si ya hiciste commit (pero no push)
git checkout -b feature/nueva-rama  # Crea rama con el commit
git checkout main
git reset --hard origin/main  # Resetea main al estado remoto
```

---

## 📅 Tu Primera Semana

### Día 1-2: Configuración
- [ ] Aceptar invitación
- [ ] Clonar repositorio
- [ ] Configurar entorno local
- [ ] Ejecutar proyecto localmente
- [ ] Leer esta guía completa

### Día 3-4: Exploración
- [ ] Navegar estructura del proyecto
- [ ] Entender modelos de datos principales
- [ ] Revisar vistas y templates
- [ ] Identificar patrones de código

### Día 5: Primera Contribución
- [ ] Crear tu primera rama
- [ ] Hacer un cambio pequeño (ej: fix typo en docs)
- [ ] Crear tu primer PR
- [ ] Experimentar el flujo completo

---

## ✨ ¡Bienvenido al equipo!

Recuerda: todos empezamos desde cero. No temas hacer preguntas, cometer errores (en tu rama 😄), y aprender. Estamos aquí para ayudarte a crecer como desarrollador.

**¡Éxito en tu práctica!** 🚀

---

*Última actualización: Septiembre 2024*
*Mantenido por: @yllorca*