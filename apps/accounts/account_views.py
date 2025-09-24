import logging

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext as _, get_language
from django.views import View

from apps.accounts.forms import Custompymemadm


logger = logging.getLogger(__name__)


class CustomLoginView(View):
    """
    Vista basada en clase para manejo de autenticación de usuarios.

    Funcionalidades:
    - GET: Muestra el formulario de login
    - POST: Procesa la autenticación con validaciones de seguridad
    - Manejo consistente de errores compatible con common.js
    - Logging de intentos de login
    - Protección contra ataques de enumeración de usuarios
    """

    def get(self, request):
        """Renderiza el formulario de login"""
        print("=== LOGIN GET REQUEST ===")

        # Redirigir si el usuario ya está autenticado
        if request.user.is_authenticated:
            print(f"Usuario ya autenticado: {request.user.username}")
            return redirect('dashboard:dashboard')  # TODO: Cambiar a panel:dashboard cuando exista

        form = Custompymemadm()
        print("Renderizando formulario de login")
        return render(request, 'signin.html', {'form': form})

    def post(self, request):
        """Procesa el login con validaciones de seguridad"""
        print("\n=== LOGIN POST REQUEST ===")

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        print(f"Username recibido: '{username}'")
        print(f"Password recibido: {'*' * len(password) if password else 'VACÍO'}")

        # Validación básica de campos
        if not username or not password:
            print("ERROR: Campos vacíos detectados")
            response_data = {
                'success': False,
                'message': 'Por favor, complete todos los campos.'
            }
            print(f"Retornando respuesta de error: {response_data}")
            return JsonResponse(response_data, status=400)

        # Logging del intento de login (sin datos sensibles)
        logger.info(f"Intento de login para usuario: {username}")

        # Usar authenticate directamente (más seguro)
        print(f"Intentando autenticar usuario: {username}")
        user = authenticate(request, username=username, password=password)
        print(f"Resultado de authenticate(): {user}")

        if user is not None:
            print(f"Usuario encontrado: {user.username}")
            if user.is_active:
                print("Usuario está activo, procediendo con login")
                # NO USAR LOGIN PARA DEBUG
                login(request, user)
                logger.info(f"Login exitoso para usuario: {username}")

                # Determinar URL de redirección
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    redirect_url = next_url
                else:
                    redirect_url = reverse('dashboard:dashboard')  # TODO: Cambiar a panel:dashboard cuando exista

                print(f"URL de redirección: {redirect_url}")

                response_data = {
                    'success': True,
                    'action': 'auto',  # ← Redirección automática
                    'redirect_url': redirect_url,
                    'message': _('Inicio de sesión exitoso. Redirigiendo...')
                }
                print(f"Retornando respuesta exitosa: {response_data}")
                return JsonResponse(response_data, status=200)
            else:
                print("ERROR: Usuario no está activo")
                logger.warning(f"Intento de login con cuenta inactiva: {username}")
                response_data = {
                    'success': False,
                    'message': _('Su cuenta está desactivada. Contacte al administrador del sistema.')
                }
                print(f"Retornando respuesta de cuenta inactiva: {response_data}")
                return JsonResponse(response_data, status=400)
        else:
            print("ERROR: authenticate() retornó None - credenciales incorrectas")
            # No revelar si el usuario existe o no (previene enumeración)
            logger.warning(f"Intento de login fallido para: {username}")
            response_data = {
                'success': False,
                'message': _('Las credenciales ingresadas no son válidas. Verifique su usuario y contraseña.')
            }
            print(f"Retornando respuesta de credenciales inválidas: {response_data}")
            print(f"Status code: 400")
            return JsonResponse(response_data, status=400)


class LogoutView(View):
    """
    LogoutView es una vista basada en clases que maneja el proceso de cierre de sesión de los usuarios. Hereda de la
    clase View integrada de Django.

    La vista maneja solicitudes GET, que realiza el cierre de sesión del usuario y lo redirige a la página de inicio de sesión.

    Atributos:
    get (method): Método para manejar solicitudes GET y realizar el cierre de sesión del usuario.

    Métodos:
    get(request): Realiza el cierre de sesión del usuario y redirige a la página de inicio de sesión.
    """

    def get(self, request):
        """
        Args:
        request (HttpRequest): Objeto HttpRequest que contiene los metadatos de la solicitud.

        Returns:
        HttpResponse: Objeto HttpResponse que redirige al usuario a la página de inicio de sesión después de realizar
        el cierre de sesión.
        """
        logout(request)
        return redirect('accounts:login')
