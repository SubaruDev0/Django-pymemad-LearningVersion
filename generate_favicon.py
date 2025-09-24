#!/usr/bin/env python3
"""
Script para generar favicon.ico con múltiples tamaños desde un PNG
"""
from PIL import Image
import os

def create_favicon(source_png, output_ico):
    """
    Crea un favicon.ico con múltiples tamaños desde un PNG
    
    Tamaños recomendados para máxima compatibilidad:
    - 16x16: Tamaño mínimo, pestañas del navegador
    - 32x32: Tamaño estándar para escritorio
    - 48x48: Windows, iconos grandes
    - 64x64: Alta resolución para Windows
    """
    
    # Abrir la imagen fuente
    img = Image.open(source_png)
    
    # Asegurar que tiene canal alpha (transparencia)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Crear versiones en diferentes tamaños
    icon_sizes = [
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64)
    ]
    
    icons = []
    for size in icon_sizes:
        # Redimensionar manteniendo la calidad
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Guardar como ICO con todos los tamaños
    icons[0].save(
        output_ico,
        format='ICO',
        sizes=icon_sizes,
        append_images=icons[1:]
    )
    
    print(f"✅ Favicon creado: {output_ico}")
    print(f"   Tamaños incluidos: {', '.join([f'{w}x{h}' for w, h in icon_sizes])}")

if __name__ == "__main__":
    # Rutas de archivos
    base_path = "/Users/yllorca/Desktop/Development/pymemaddir/static/assets/app-icons"
    source_file = os.path.join(base_path, "pymemad.png")
    output_file = os.path.join(base_path, "favicon.ico")
    
    # Hacer backup del favicon existente si existe
    if os.path.exists(output_file):
        backup_file = os.path.join(base_path, "favicon.ico.backup")
        os.rename(output_file, backup_file)
        print(f"📦 Backup creado: {backup_file}")
    
    # Generar el nuevo favicon
    try:
        create_favicon(source_file, output_file)
    except Exception as e:
        print(f"❌ Error: {e}")
        # Restaurar backup si falló
        if os.path.exists(backup_file):
            os.rename(backup_file, output_file)
            print("🔄 Backup restaurado")
