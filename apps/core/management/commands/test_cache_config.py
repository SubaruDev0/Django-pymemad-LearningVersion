# management/commands/test_cache_config.py
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings

User = get_user_model()


class Command(BaseCommand):
    help = 'Prueba la configuración del cache y middleware'

    def handle(self, *args, **options):
        self.stdout.write("\n🔍 Probando configuración de cache...\n")

        # 1. Probar cache básico
        self.stdout.write("1. Probando cache básico:")
        cache.set('test_key', 'test_value', 30)
        value = cache.get('test_key')
        if value == 'test_value':
            self.stdout.write(self.style.SUCCESS("   ✅ Cache básico funcionando"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ Cache básico NO funciona"))

        # 2. Crear clientes de prueba
        client_anon = Client()
        client_staff = Client()

        # Crear usuario staff de prueba
        staff_user, created = User.objects.get_or_create(
            username='test_staff',
            defaults={'is_staff': True, 'is_active': True}
        )
        if created:
            staff_user.set_password('test123')
            staff_user.save()

        client_staff.force_login(staff_user)

        # 3. Determinar URL de prueba (con idioma)
        # Usar el idioma por defecto
        lang_code = settings.LANGUAGE_CODE
        test_urls = [
            f'/{lang_code}/',  # Home con idioma
            f'/{lang_code}/news/',  # Lista de noticias (según las vistas reales)
            f'/{lang_code}/about/',  # Página sobre nosotros
            f'/{lang_code}/members/',  # Directorio de miembros
        ]

        # 4. Probar respuestas para usuario anónimo
        self.stdout.write("\n2. Probando cache para usuario anónimo:")
        for url in test_urls:
            self.stdout.write(f"\n   URL: {url}")
            response = client_anon.get(url, follow=True)  # Seguir redirecciones

            # Obtener la respuesta final después de redirecciones
            if response.redirect_chain:
                self.stdout.write(f"   Redirigido a: {response.redirect_chain[-1][0]}")

            headers = dict(response.headers) if hasattr(response, 'headers') else {}

            self.stdout.write(f"   Status: {response.status_code}")
            self.stdout.write(
                f"   Cache-Control: {headers.get('Cache-Control', response.get('Cache-Control', 'No establecido'))}")
            self.stdout.write(
                f"   X-Cache-Status: {headers.get('X-Cache-Status', response.get('X-Cache-Status', 'No establecido'))}")

            # Verificar si se está cacheando
            vary = headers.get('Vary', response.get('Vary', ''))
            if vary:
                self.stdout.write(f"   Vary: {vary}")

        # 5. Probar respuestas para staff
        self.stdout.write("\n3. Probando cache para usuario staff:")
        for url in test_urls:
            self.stdout.write(f"\n   URL: {url}")
            response = client_staff.get(url, follow=True)

            if response.redirect_chain:
                self.stdout.write(f"   Redirigido a: {response.redirect_chain[-1][0]}")

            headers = dict(response.headers) if hasattr(response, 'headers') else {}

            self.stdout.write(f"   Status: {response.status_code}")
            cache_control = headers.get('Cache-Control', response.get('Cache-Control', 'No establecido'))
            self.stdout.write(f"   Cache-Control: {cache_control}")
            self.stdout.write(
                f"   X-Cache-Status: {headers.get('X-Cache-Status', response.get('X-Cache-Status', 'No establecido'))}")

            if 'no-cache' in cache_control or 'BYPASS' in headers.get('X-Cache-Status', ''):
                self.stdout.write(self.style.SUCCESS("   ✅ Staff bypass funcionando"))
            else:
                self.stdout.write(self.style.ERROR("   ❌ Staff bypass NO funciona"))

        # 6. Probar dashboard
        self.stdout.write("\n4. Probando cache del dashboard:")
        dashboard_urls = [f'/{lang_code}/dashboard/', f'/{lang_code}/dashboard/members/', f'/{lang_code}/dashboard/billing/']

        for url in dashboard_urls:
            self.stdout.write(f"\n   URL: {url}")
            response = client_staff.get(url, follow=True)
            headers = dict(response.headers) if hasattr(response, 'headers') else {}

            self.stdout.write(f"   Status: {response.status_code}")
            cache_control = headers.get('Cache-Control', response.get('Cache-Control', 'No establecido'))
            self.stdout.write(f"   Cache-Control: {cache_control}")

            if 'no-cache' in cache_control:
                self.stdout.write(self.style.SUCCESS("   ✅ Panel excluido del cache"))
            else:
                self.stdout.write(self.style.ERROR("   ❌ Panel NO excluido del cache"))

        # 7. Verificar middleware cargado
        self.stdout.write("\n5. Verificando middleware:")

        middleware_order = []
        for mw in settings.MIDDLEWARE:
            if 'Cache' in mw or 'cache' in mw:
                middleware_order.append(mw)

        self.stdout.write("   Orden de middleware de cache:")
        for i, mw in enumerate(middleware_order):
            self.stdout.write(f"   {i + 1}. {mw.split('.')[-1]}")

        # 8. Probar que el cache funciona
        self.stdout.write("\n6. Probando funcionamiento del cache:")

        # Primera petición (MISS)
        url = f'/{lang_code}/news/'
        response1 = client_anon.get(url)

        # Segunda petición (debería ser HIT)
        response2 = client_anon.get(url)

        # Verificar si la segunda fue más rápida (indicador de cache)
        self.stdout.write(f"   Primera petición: {response1.status_code}")
        self.stdout.write(f"   Segunda petición: {response2.status_code}")

        # 9. Estadísticas del cache
        self.stdout.write("\n7. Estadísticas del cache:")
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            info = redis_conn.info()
            self.stdout.write(f"   Keys en Redis: {redis_conn.dbsize()}")
            self.stdout.write(f"   Memoria usada: {info.get('used_memory_human', 'N/A')}")
        except Exception as e:
            self.stdout.write(f"   Error obteniendo stats: {e}")

        # Limpiar
        if created:
            staff_user.delete()
        cache.delete('test_key')

        self.stdout.write(self.style.SUCCESS("\n✨ Prueba completada"))
