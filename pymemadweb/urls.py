from django.contrib import admin, sitemaps
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from apps.landing.views import manifest_view


# URLs sin prefijo de idioma
# (APIs, webhooks, archivos estáticos, etc.)
urlpatterns = [
    # URLs para cambiar el idioma - DEBE estar fuera de i18n_patterns
    path('i18n/', include('django.conf.urls.i18n')),

    # Web App Manifest
    path('manifest.json', manifest_view, name='manifest'),

    # CAPTCHA y otros servicios técnicos
    path('captcha/', include('captcha.urls')),

    # Health check y readiness endpoints para Kubernetes
    path('core/', include('apps.core.urls')),

    path('sitemap.xml', sitemap, {
        'sitemaps': sitemaps,
        'template_name': 'sitemaps/blog_sitemap.xml',  # Plantilla simplificada
        'content_type': 'application/xml'
    }, name='django.contrib.sitemaps.views.sitemap'),

]

# URLs con prefijo de idioma
# (Todas las páginas visibles para el usuario)
urlpatterns += i18n_patterns(
    # Panel de administración
    path('admin/', admin.site.urls),

    # Páginas principales del sitio
    path('', include('apps.landing.urls')),
    path('dashboard/', include('apps.panel.urls')),

    # Autenticación y cuentas
    path('accounts/', include('apps.accounts.urls')),

    # Sistema de permisos ACL
    path('permissions/', include('apps.permissions.urls')),
    # Usar True muestra /es/ incluso para el idioma por defecto
    # Usar False ocultará el prefijo para el idioma por defecto
    prefix_default_language=True,
)

# Manejadores de errores personalizados
handler403 = 'apps.core.error_views.permission_denied_view'
handler404 = 'apps.core.error_views.page_not_found_view'
handler500 = 'apps.core.error_views.server_error_view'
