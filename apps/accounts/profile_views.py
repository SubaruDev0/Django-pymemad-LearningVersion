# apps/accounts/profile_views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from .forms import CustomPasswordChangeForm, ProfileUpdateForm, AvatarUpdateForm


@method_decorator(never_cache, name='dispatch')
class ProfileSettingsView(LoginRequiredMixin, View):
    """
    Vista principal que muestra todos los formularios de configuración del perfil.
    """
    template_name = 'profile-settings.html'

    def get(self, request):
        context = {
            'profile_form': ProfileUpdateForm(instance=request.user),
            'avatar_form': AvatarUpdateForm(instance=request.user),
            'password_form': CustomPasswordChangeForm(user=request.user),
            'user': request.user
        }
        return render(request, self.template_name, context)


@method_decorator(never_cache, name='dispatch')
class ProfileUpdateView(LoginRequiredMixin, View):
    """
    Vista para actualizar datos del perfil vía AJAX.
    """
    def post(self, request):
        form = ProfileUpdateForm(data=request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': 'Perfil actualizado exitosamente'
            })
        else:
            errors = {}
            for field, error_list in form.errors.items():
                field_label = form.fields[field].label or field.replace('_', ' ').title()
                errors[field] = {
                    'messages': [str(e) for e in error_list],
                    'field_label': field_label
                }
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrija los errores en el formulario',
                'errors': errors
            }, status=400)


@method_decorator(never_cache, name='dispatch')
class AvatarUpdateView(LoginRequiredMixin, View):
    """
    Vista para actualizar la foto de perfil vía AJAX.
    """
    def post(self, request):
        # Guardar referencia al avatar anterior
        old_avatar = None
        if request.user.avatar:
            old_avatar = request.user.avatar

        form = AvatarUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            # Generar timestamp para evitar caché
            import time
            cache_buster = int(time.time())

            # Construir URL con timestamp
            avatar_url = f"{user.avatar.url}?t={cache_buster}" if user.avatar else None

            # Eliminar avatar anterior de S3 (si existe y es diferente)
            if old_avatar and old_avatar != user.avatar:
                try:
                    old_avatar.delete(save=False)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error al eliminar avatar anterior: {str(e)}")

            return JsonResponse({
                'success': True,
                'message': 'Foto de perfil actualizada exitosamente',
                'avatar_url': avatar_url,
                'cache_buster': cache_buster,
                'avatar_name': str(user.avatar) if user.avatar else None
            })
        else:
            errors = {}
            for field, error_list in form.errors.items():
                field_label = form.fields[field].label or field.replace('_', ' ').title()
                errors[field] = {
                    'messages': [str(e) for e in error_list],
                    'field_label': field_label
                }
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrija los errores en el formulario',
                'errors': errors
            }, status=400)


@method_decorator(never_cache, name='dispatch')
class AvatarDeleteView(LoginRequiredMixin, View):
    """
    Vista para eliminar la foto de perfil vía AJAX.
    """
    def post(self, request):
        if request.user.avatar:
            try:
                # Eliminar archivo de S3
                request.user.avatar.delete(save=False)
                # Limpiar el campo en la BD
                request.user.avatar = None
                request.user.save(update_fields=['avatar'])
                return JsonResponse({
                    'success': True,
                    'message': 'Foto de perfil eliminada exitosamente'
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error al eliminar avatar: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': 'Error al eliminar la foto de perfil'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'message': 'No hay foto de perfil para eliminar'
            }, status=400)


@method_decorator(never_cache, name='dispatch')
class PasswordChangeView(LoginRequiredMixin, View):
    """
    Vista para cambiar la contraseña del usuario autenticado vía AJAX.
    """
    def post(self, request):
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Mantener la sesión activa después del cambio
            update_session_auth_hash(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Contraseña actualizada exitosamente'
            })
        else:
            # Construir errores con etiquetas en español
            errors = {}
            for field, error_list in form.errors.items():
                field_label = {
                    'old_password': 'Contraseña actual',
                    'new_password1': 'Nueva contraseña',
                    'new_password2': 'Confirmar contraseña'
                }.get(field, field.replace('_', ' ').title())
                errors[field] = {
                    'messages': [str(e) for e in error_list],
                    'field_label': field_label
                }
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrige los errores en el formulario',
                'errors': errors
            }, status=400)