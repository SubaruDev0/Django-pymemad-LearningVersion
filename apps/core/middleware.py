from django.utils import timezone
import pytz


class TimezoneMiddleware:
    """
    Middleware para activar la zona horaria de Chile en todas las requests.
    Esto asegura que las fechas se muestren consistentemente en Chile timezone.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Activar timezone de Chile para toda la request
        timezone.activate(pytz.timezone('America/Santiago'))
        
        response = self.get_response(request)
        
        return response