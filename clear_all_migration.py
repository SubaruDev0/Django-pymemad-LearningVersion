#!/usr/bin/env python
"""
Script para limpiar todas las migraciones de Django.
Solo elimina migraciones de las apps del proyecto, no de las apps de Django o terceros.
"""
import os
import glob
import django
from django.apps import apps

# Carga las configuraciones de Django para pymemad
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pymemadweb.settings')

# Asegúrate de que Django ha cargado todas sus aplicaciones
django.setup()

# Lista de apps del proyecto (no Django ni terceros)
PROJECT_APPS = [
    'accounts',
    'blog',
    'contact',
    'content',
    'core',
    'homepage',
    'news',
    'api',
    # Agrega aquí otras apps del proyecto si las hay
]

print("=== Iniciando limpieza de migraciones ===")
print(f"Apps a procesar: {', '.join(PROJECT_APPS)}")

# Contador de migraciones eliminadas
total_removed = 0

# Recorre solo las aplicaciones del proyecto
for app_config in apps.get_app_configs():
    # Solo procesar apps del proyecto
    if app_config.label not in PROJECT_APPS:
        continue
    
    print(f"\nProcesando app: {app_config.label}")
    
    # Si la aplicación tiene una carpeta de migraciones
    migration_folder = os.path.join(app_config.path, 'migrations')
    if os.path.isdir(migration_folder):
        # Patrón para encontrar todos los archivos .py (excluyendo __init__.py)
        file_pattern = os.path.join(migration_folder, '[!__init__]*.py')
        # También eliminar archivos .pyc
        pyc_pattern = os.path.join(migration_folder, '*.pyc')
        pycache_pattern = os.path.join(migration_folder, '__pycache__')
        
        # Encuentra todos los archivos que coinciden con el patrón
        migration_files = glob.glob(file_pattern)
        pyc_files = glob.glob(pyc_pattern)
        
        # Elimina cada archivo de migración
        for file_name in migration_files:
            try:
                os.remove(file_name)
                print(f'  ✓ Eliminado: {os.path.basename(file_name)}')
                total_removed += 1
            except OSError as e:
                print(f'  ✗ Error al eliminar {file_name}: {e}')
        
        # Elimina archivos .pyc
        for file_name in pyc_files:
            try:
                os.remove(file_name)
            except OSError:
                pass
        
        # Elimina carpeta __pycache__ si existe
        if os.path.exists(pycache_pattern):
            try:
                import shutil
                shutil.rmtree(pycache_pattern)
            except OSError:
                pass
        
        # NO intentar hacer migrate zero en producción, es peligroso
        # Solo limpiar archivos de migración locales
    else:
        print(f'  ⚠ No se encontró carpeta de migraciones')

print(f"\n=== Limpieza completada ===")
print(f"Total de migraciones eliminadas: {total_removed}")
print("Las nuevas migraciones se crearán con makemigrations")
