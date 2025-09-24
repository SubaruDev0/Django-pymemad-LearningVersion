# apps/core/management/commands/clear_cache.py

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django_redis import get_redis_connection
from datetime import datetime
import time


class Command(BaseCommand):
    help = 'Limpia la cache del sitio con opciones avanzadas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar limpieza sin confirmación',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Mostrar solo estadísticas sin limpiar',
        )
        parser.add_argument(
            '--pattern',
            type=str,
            help='Limpiar solo keys que coincidan con el patrón',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['all', 'news', 'members', 'magazine', 'pages', 'sessions', 'home', 'dashboard'],
            default='all',
            help='Tipo de cache a limpiar',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se limpiaría sin hacerlo realmente',
        )

    def handle(self, *args, **options):
        if options['stats']:
            self.show_stats()
            return

        if options['pattern']:
            self.clear_pattern(options['pattern'], dry_run=options['dry_run'])
            return

        # Confirmación en producción
        if not settings.DEBUG and not options['force'] and not options['dry_run']:
            self.stdout.write(self.style.WARNING('⚠️  ADVERTENCIA: Estás en PRODUCCIÓN'))
            self.stdout.write(
                f'Esta acción eliminará {"TODA" if options["type"] == "all" else options["type"].upper()} la cache del sitio.')
            confirm = input('¿Estás seguro? (escribe "SI" para continuar): ')
            if confirm != 'SI':
                self.stdout.write(self.style.ERROR('Operación cancelada'))
                return

        if options['type'] == 'all':
            self.clear_all_cache(dry_run=options['dry_run'])
        else:
            self.clear_by_type(options['type'], dry_run=options['dry_run'])

    def get_redis_connection(self):
        """Obtiene la conexión a Redis usando django-redis"""
        try:
            return get_redis_connection("default")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error conectando a Redis: {e}'))
            return None

    def clear_all_cache(self, dry_run=False):
        """Limpia toda la cache"""
        self.stdout.write('=' * 60)
        self.stdout.write(f' LIMPIEZA {"SIMULADA" if dry_run else "COMPLETA"} DE CACHE')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Fecha/Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Entorno: {"PRODUCCIÓN" if not settings.DEBUG else "DESARROLLO"}')

        # Mostrar estadísticas antes
        self.show_stats()

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 MODO DRY-RUN: No se eliminará nada'))
            return

        try:
            # Método 1: Usar cache.clear() de Django
            self.stdout.write('\n📌 Limpiando con cache.clear()...')
            cache.clear()
            self.stdout.write(self.style.SUCCESS('✅ Cache principal limpiado'))

            # Método 2: Limpiar directamente en Redis para asegurar
            redis_conn = self.get_redis_connection()
            if redis_conn:
                self.stdout.write('\n📌 Limpiando directamente en Redis...')

                # Usar FLUSHDB solo si estamos seguros
                if settings.DEBUG or input('¿Ejecutar FLUSHDB? (SI/no): ').upper() == 'SI':
                    redis_conn.flushdb()
                    self.stdout.write(self.style.SUCCESS('✅ Redis FLUSHDB ejecutado'))
                else:
                    # Alternativa: eliminar por patrón
                    deleted = self._delete_by_pattern(redis_conn, '*')
                    self.stdout.write(self.style.SUCCESS(f'✅ {deleted} keys eliminadas'))

            # Esperar un momento para asegurar propagación
            time.sleep(0.5)

            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS(' ✅ CACHE LIMPIADO COMPLETAMENTE'))
            self.stdout.write('=' * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()

    def clear_by_type(self, cache_type, dry_run=False):
        """Limpia un tipo específico de cache"""
        patterns = {
            'news': ['*news*', '*noticias*', '*noticia*'],
            'members': ['*members*', '*miembros*', '*directory*'],
            'magazine': ['*magazine*', '*revista*'],
            'pages': ['*page*', '*about*', '*join*', '*contact*', '*views.decorators.cache*'],
            'sessions': ['*session*'],
            'home': ['*home*', '*index*', '*:1:/*'],
            'dashboard': ['*dashboard*', '*panel*', '*billing*', '*expenses*', '*balance*'],
        }

        if cache_type not in patterns:
            self.stdout.write(self.style.ERROR(f'Tipo de cache no válido: {cache_type}'))
            return

        self.stdout.write(f'\n🎯 Limpiando cache tipo: {cache_type.upper()}')

        redis_conn = self.get_redis_connection()
        if not redis_conn:
            return

        total_deleted = 0
        for pattern in patterns[cache_type]:
            if dry_run:
                count = self._count_keys(redis_conn, pattern)
                self.stdout.write(f'  Patrón "{pattern}": {count} keys')
            else:
                deleted = self._delete_by_pattern(redis_conn, pattern)
                total_deleted += deleted
                if deleted > 0:
                    self.stdout.write(f'  Patrón "{pattern}": {deleted} keys eliminadas')

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Total eliminadas: {total_deleted} keys'))

    def clear_pattern(self, pattern, dry_run=False):
        """Limpia keys por patrón específico"""
        self.stdout.write(f'\n🔍 {"Buscando" if dry_run else "Limpiando"} keys con patrón: "{pattern}"')

        redis_conn = self.get_redis_connection()
        if not redis_conn:
            return

        if dry_run:
            count = self._count_keys(redis_conn, pattern)
            self.stdout.write(f'Encontradas: {count} keys')

            # Mostrar algunas keys de ejemplo
            sample_keys = []
            cursor = 0
            key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
            full_pattern = f"{key_prefix}:*{pattern}*" if key_prefix else f"*{pattern}*"

            while len(sample_keys) < 10:
                cursor, keys = redis_conn.scan(cursor, match=full_pattern, count=100)
                sample_keys.extend(keys[:10 - len(sample_keys)])
                if cursor == 0:
                    break

            if sample_keys:
                self.stdout.write('\nEjemplos de keys que se eliminarían:')
                for key in sample_keys:
                    self.stdout.write(f'  - {key.decode("utf-8")}')
        else:
            deleted = self._delete_by_pattern(redis_conn, pattern)
            self.stdout.write(self.style.SUCCESS(f'✅ {deleted} keys eliminadas'))

    def _delete_by_pattern(self, redis_conn, pattern):
        """Elimina keys por patrón y retorna el conteo"""
        key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
        full_pattern = f"{key_prefix}:*{pattern}*" if key_prefix else f"*{pattern}*"

        deleted_count = 0
        cursor = 0

        # Usar pipeline para mejor rendimiento
        pipe = redis_conn.pipeline()

        while True:
            cursor, keys = redis_conn.scan(cursor, match=full_pattern, count=1000)
            if keys:
                for key in keys:
                    pipe.delete(key)

                # Ejecutar pipeline cada 1000 comandos
                if len(pipe) >= 1000:
                    results = pipe.execute()
                    deleted_count += sum(1 for r in results if r)
                    pipe = redis_conn.pipeline()

            if cursor == 0:
                break

        # Ejecutar comandos restantes
        if len(pipe) > 0:
            results = pipe.execute()
            deleted_count += sum(1 for r in results if r)

        return deleted_count

    def _count_keys(self, redis_conn, pattern):
        """Cuenta keys por patrón"""
        key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
        full_pattern = f"{key_prefix}:*{pattern}*" if key_prefix else f"*{pattern}*"

        count = 0
        cursor = 0

        while True:
            cursor, keys = redis_conn.scan(cursor, match=full_pattern, count=1000)
            count += len(keys)
            if cursor == 0:
                break

        return count

    def show_stats(self):
        """Muestra estadísticas detalladas de cache"""
        self.stdout.write('\n📊 ESTADÍSTICAS DE CACHE:')
        self.stdout.write('-' * 50)

        # Información básica
        backend = settings.CACHES["default"]["BACKEND"]
        self.stdout.write(f'Backend: {backend}')
        self.stdout.write(f'Location: {settings.CACHES["default"]["LOCATION"]}')
        self.stdout.write(f'Key Prefix: {settings.CACHES["default"].get("KEY_PREFIX", "ninguno")}')
        self.stdout.write(f'Timeout default: {settings.CACHES["default"].get("TIMEOUT", "N/A")} segundos')

        redis_conn = self.get_redis_connection()
        if not redis_conn:
            return

        try:
            # Información de Redis
            info = redis_conn.info()
            memory_info = redis_conn.info('memory')
            stats = redis_conn.info('stats')

            self.stdout.write(f'\nServidor Redis:')
            self.stdout.write(f'  Versión: {info.get("redis_version", "N/A")}')
            self.stdout.write(f'  Uptime: {info.get("uptime_in_days", "N/A")} días')
            self.stdout.write(f'  Clientes conectados: {info.get("connected_clients", "N/A")}')

            self.stdout.write(f'\nMemoria:')
            self.stdout.write(f'  Usada: {memory_info.get("used_memory_human", "N/A")}')
            self.stdout.write(f'  Pico: {memory_info.get("used_memory_peak_human", "N/A")}')
            self.stdout.write(f'  RSS: {memory_info.get("used_memory_rss_human", "N/A")}')

            # Total de keys
            total_keys = redis_conn.dbsize()
            self.stdout.write(f'\nTotal keys en DB: {total_keys:,}')

            # Hit rate
            hits = stats.get('keyspace_hits', 0)
            misses = stats.get('keyspace_misses', 0)
            total_ops = hits + misses

            if total_ops > 0:
                hit_rate = (hits / total_ops) * 100
                self.stdout.write(f'\nRendimiento:')
                self.stdout.write(f'  Hits: {hits:,}')
                self.stdout.write(f'  Misses: {misses:,}')
                self.stdout.write(f'  Hit Rate: {hit_rate:.2f}%')
                self.stdout.write(f'  Comandos/seg: {stats.get("instantaneous_ops_per_sec", "N/A")}')

            # Contar keys por tipo
            key_prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
            patterns = {
                'Cache de vistas': f"{key_prefix}:*views.decorators.cache*",
                'Cache del middleware': f"{key_prefix}:*GET*",
                'Posts del blog': f"{key_prefix}:*post*",
                'Páginas home': f"{key_prefix}:*home*",
                'Listas de noticias': f"{key_prefix}:*news*",
                'Categorías': f"{key_prefix}:*category*",
                'Tags': f"{key_prefix}:*tag*",
                'Sesiones': f"{key_prefix}:*session*",
                'Template tags': f"{key_prefix}:*latest_posts*",
                'Celery': f"{key_prefix}:*celery*",
            }

            self.stdout.write('\nDistribución de keys:')
            pattern_total = 0

            for name, pattern in patterns.items():
                count = self._count_keys(redis_conn, pattern.replace(f"{key_prefix}:", ""))
                if count > 0:
                    pattern_total += count
                    percentage = (count / total_keys * 100) if total_keys > 0 else 0
                    self.stdout.write(f'  {name}: {count:,} ({percentage:.1f}%)')

            # Keys sin clasificar
            if total_keys > pattern_total:
                other_keys = total_keys - pattern_total
                other_percentage = (other_keys / total_keys * 100) if total_keys > 0 else 0
                self.stdout.write(f'  Otros: {other_keys:,} ({other_percentage:.1f}%)')

            # Top 10 keys más grandes (opcional)
            self.stdout.write('\nKeys más grandes:')
            cursor = 0
            key_sizes = []

            # Muestrear algunas keys
            sample_size = min(1000, total_keys)
            sampled = 0

            while sampled < sample_size:
                cursor, keys = redis_conn.scan(cursor, count=100)
                for key in keys:
                    try:
                        size = redis_conn.memory_usage(key)
                        if size:
                            key_sizes.append((key.decode('utf-8'), size))
                            sampled += 1
                    except:
                        pass
                if cursor == 0:
                    break

            # Mostrar top 10
            key_sizes.sort(key=lambda x: x[1], reverse=True)
            for key, size in key_sizes[:10]:
                size_human = self._human_readable_size(size)
                # Truncar key si es muy larga
                display_key = key if len(key) <= 60 else key[:57] + '...'
                self.stdout.write(f'  {display_key}: {size_human}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error obteniendo estadísticas: {e}'))

    def _human_readable_size(self, size_bytes):
        """Convierte bytes a formato legible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
