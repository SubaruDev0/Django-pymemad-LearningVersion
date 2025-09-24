from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse


def manifest_view(request):
    """
    Generate dynamic web app manifest.json
    """
    manifest = {
        "name": "PyMemadWeb",
        "short_name": "PyMemad",
        "description": "Sistema de monitoreo de noticias y medios",
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#448c74",
        "background_color": "#ffffff",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": f"{settings.STATIC_URL}assets/app-icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": f"{settings.STATIC_URL}assets/app-icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": f"{settings.STATIC_URL}assets/app-icons/icon-180x180.png",
                "sizes": "180x180",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "categories": ["news", "productivity", "utilities"]
    }
    
    return JsonResponse(manifest, content_type='application/manifest+json')