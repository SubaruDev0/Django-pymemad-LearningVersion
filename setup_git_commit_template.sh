#!/bin/bash

echo "==================================="
echo "   Configurando Plantilla de Commit"
echo "==================================="
echo ""

# Configurar la plantilla de commit para este repositorio
git config --local commit.template .gitmessage

echo "✅ Plantilla configurada para este repositorio"
echo ""

# Preguntar si quiere configurarla globalmente
read -p "¿Deseas usar esta plantilla en TODOS tus repositorios? (s/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    # Copiar plantilla a home
    cp .gitmessage ~/.gitmessage
    # Configurar globalmente
    git config --global commit.template ~/.gitmessage
    echo "✅ Plantilla configurada globalmente"
else
    echo "ℹ️  Plantilla configurada solo para este repositorio"
fi

echo ""
echo "==================================="
echo "   Cómo usar la plantilla"
echo "==================================="
echo ""
echo "1. Para commits normales:"
echo "   git commit"
echo "   (Se abrirá tu editor con la plantilla)"
echo ""
echo "2. Para commits rápidos (sin plantilla):"
echo "   git commit -m 'mensaje rápido'"
echo ""
echo "3. Para ver la plantilla:"
echo "   cat .gitmessage"
echo ""
echo "==================================="
echo "   Ejemplos de buenos commits"
echo "==================================="
echo ""
echo "✅ BUENOS ejemplos:"
echo "   feat: agregar integración con Sentry para monitoreo de errores"
echo "   fix: corregir conexión de Redis en Celery workers"
echo "   ci: agregar reinicio automático de pods al actualizar secrets"
echo "   refactor: limpiar migraciones y usar script de sigescap"
echo ""
echo "❌ MALOS ejemplos:"
echo "   'update files'"
echo "   'fix bug'"
echo "   'cambios varios'"
echo "   'wip'"
echo ""
echo "==================================="
echo "   Configuración adicional"
echo "==================================="
echo ""
echo "Para cambiar tu editor de commits (recomendado: VS Code):"
echo "   git config --global core.editor 'code --wait'"
echo ""
echo "Para vim:"
echo "   git config --global core.editor vim"
echo ""
echo "Para nano:"
echo "   git config --global core.editor nano"
echo ""