from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import time

# Create your views here.

def health_check(request):
    """
    Health check endpoint para Kubernetes.
    Verifica que Django y la base de datos estén funcionando.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
        return JsonResponse(health_status, status=503)
    
    # Check cache (if configured)
    try:
        cache.set('health_check', 'ok', 1)
        if cache.get('health_check') == 'ok':
            health_status["checks"]["cache"] = "ok"
        else:
            health_status["checks"]["cache"] = "not configured"
    except:
        health_status["checks"]["cache"] = "not configured"
    
    return JsonResponse(health_status)

def readiness_check(request):
    """
    Readiness check endpoint para Kubernetes.
    Verifica que la aplicación esté lista para recibir tráfico.
    """
    try:
        # Quick database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ready"})
    except:
        return JsonResponse({"status": "not ready"}, status=503)
