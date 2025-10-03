"""
Vistas personalizadas para manejo de errores HTTP
"""
from django.shortcuts import render


def permission_denied_view(request, exception=None):
    """
    Vista personalizada para error 403 - Acceso Denegado
    """
    context = {
        'exception': exception,
    }
    return render(request, '403.html', context, status=403)


def page_not_found_view(request, exception=None):
    """
    Vista personalizada para error 404 - Página No Encontrada
    """
    context = {
        'exception': exception,
    }
    return render(request, '404.html', context, status=404)


def server_error_view(request, exception=None):
    """
    Vista personalizada para error 500 - Error del Servidor
    """
    context = {
        'exception': exception,
    }
    return render(request, '500.html', context, status=500)
