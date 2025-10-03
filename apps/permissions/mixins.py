"""
Mixins para el sistema de permisos ACL.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .models import Module, RoleModuleAccess
from .constants import get_module_actions


class ACLPermissionMixin(LoginRequiredMixin):
    """
    Mixin que agrega funcionalidad de permisos ACL a las vistas.

    Uso:
        class MyView(ACLPermissionMixin, ListView):
            module_code = 'members'
            required_action = 'view'
    """
    module_code = None  # Debe ser definido en la vista
    required_action = None  # Acción requerida para acceder a la vista

    def dispatch(self, request, *args, **kwargs):
        """Verifica permisos antes de procesar la vista."""
        if not self.has_permission():
            raise PermissionDenied("No tiene permisos para realizar esta acción.")
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        """
        Verifica si el usuario tiene el permiso requerido.

        Returns:
            bool: True si tiene permiso, False en caso contrario
        """
        # Superusuarios siempre tienen acceso
        if self.request.user.is_superuser:
            return True

        # Si no hay módulo o acción definida, permitir acceso (retrocompatibilidad)
        if not self.module_code or not self.required_action:
            return True

        # Verificar si el usuario tiene rol configurado
        role_id = self.request.session.get('role_id')
        if not role_id:
            # Si no hay rol en sesión, intentar obtener el rol primario del usuario
            if hasattr(self.request.user, 'primary_role') and self.request.user.primary_role:
                role_id = self.request.user.primary_role.id
                self.request.session['role_id'] = role_id
                self.request.session['role_name'] = self.request.user.primary_role.name
            else:
                return False

        # Verificar permisos del rol
        permissions = self.get_user_permissions()
        action_key = f'can_{self.required_action}'

        return permissions.get(action_key, False)

    def get_user_permissions(self):
        """
        Obtiene todos los permisos del usuario para el módulo actual.

        Returns:
            dict: Diccionario con los permisos del usuario
        """
        permissions = {
            'can_view': False,
            'can_add': False,
            'can_change': False,
            'can_delete': False,
            'can_import': False,
            'can_export': False,
            'can_assign': False,
            'can_approve': False,
            'can_reject': False,
            'can_bulk_update': False,
            'can_manage_members': False,
            'can_manage_payments': False,
            'can_send_notification': False,
            'can_view_reports': False,
            'can_generate_report': False,
            'can_view_sensitive': False,
        }

        # Si no hay módulo definido, retornar sin permisos
        if not self.module_code:
            return permissions

        # Si es superusuario, todos los permisos
        if self.request.user.is_superuser:
            return {key: True for key in permissions.keys()}

        try:
            # Obtener el rol del usuario
            role_id = self.request.session.get('role_id')
            if not role_id and hasattr(self.request.user, 'primary_role') and self.request.user.primary_role:
                role_id = self.request.user.primary_role.id

            if not role_id:
                return permissions

            # Obtener el módulo
            module = Module.objects.filter(code=self.module_code).first()
            if not module:
                return permissions

            # Obtener el acceso del rol al módulo
            access = RoleModuleAccess.objects.filter(
                role_id=role_id,
                module=module
            ).first()

            if access and access.enabled_actions:
                # Mapear las acciones habilitadas a los permisos
                for action in access.enabled_actions:
                    permission_key = f'can_{action}'
                    permissions[permission_key] = True

                    # Mapeos especiales para compatibilidad
                    if action == 'add':
                        permissions['can_create'] = True  # Alias
                    elif action == 'change':
                        permissions['can_edit'] = True  # Alias

        except Exception as e:
            print(f"Error obteniendo permisos ACL: {e}")

        return permissions

    def get_context_data(self, **kwargs):
        """
        Agrega los permisos ACL al contexto.
        """
        context = super().get_context_data(**kwargs)
        context['acl_permissions'] = self.get_user_permissions()
        context['module_code'] = self.module_code

        # Información del rol actual
        context['current_role'] = {
            'id': self.request.session.get('role_id'),
            'name': self.request.session.get('role_name', 'Sin rol')
        }

        # Acciones disponibles para el módulo
        if self.module_code:
            context['module_actions'] = get_module_actions(self.module_code)

        return context


class BulkActionMixin:
    """
    Mixin para manejar acciones masivas en vistas de lista.
    """

    def get_selected_ids(self):
        """
        Obtiene los IDs seleccionados desde el request.

        Returns:
            list: Lista de IDs seleccionados
        """
        if self.request.method == 'POST':
            return self.request.POST.getlist('selected_ids[]')
        return []

    def process_bulk_action(self, action, selected_ids):
        """
        Procesa una acción masiva sobre los elementos seleccionados.

        Args:
            action (str): Acción a realizar
            selected_ids (list): Lista de IDs seleccionados

        Returns:
            dict: Resultado de la operación
        """
        # Este método debe ser sobrescrito en la vista
        raise NotImplementedError("Debe implementar process_bulk_action en su vista")

    def handle_bulk_request(self):
        """
        Maneja una petición de acción masiva.

        Returns:
            JsonResponse: Respuesta JSON con el resultado
        """
        from django.http import JsonResponse

        action = self.request.POST.get('bulk_action')
        selected_ids = self.get_selected_ids()

        if not action:
            return JsonResponse({
                'success': False,
                'message': 'No se especificó una acción'
            }, status=400)

        if not selected_ids:
            return JsonResponse({
                'success': False,
                'message': 'No se seleccionaron elementos'
            }, status=400)

        # Verificar permisos para la acción
        if hasattr(self, 'required_action'):
            self.required_action = action
            if not self.has_permission():
                return JsonResponse({
                    'success': False,
                    'message': 'No tiene permisos para realizar esta acción'
                }, status=403)

        try:
            result = self.process_bulk_action(action, selected_ids)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)


class RoleRequiredMixin:
    """
    Mixin que requiere que el usuario tenga un rol específico.
    """
    required_roles = []  # Lista de códigos de roles permitidos
    required_level = None  # Nivel mínimo requerido

    def dispatch(self, request, *args, **kwargs):
        if not self.has_required_role():
            raise PermissionDenied("No tiene el rol necesario para acceder a esta sección.")
        return super().dispatch(request, *args, **kwargs)

    def has_required_role(self):
        """
        Verifica si el usuario tiene uno de los roles requeridos.
        """
        # Superusuarios siempre tienen acceso
        if self.request.user.is_superuser:
            return True

        # Si no hay roles requeridos, permitir acceso
        if not self.required_roles and not self.required_level:
            return True

        # Verificar rol del usuario
        if hasattr(self.request.user, 'primary_role') and self.request.user.primary_role:
            user_role = self.request.user.primary_role

            # Verificar por código de rol
            if self.required_roles and user_role.code in self.required_roles:
                return True

            # Verificar por nivel de rol
            if self.required_level:
                role_levels = {
                    'super_admin': 7,
                    'admin': 6,
                    'board_member': 5,
                    'treasurer': 4,
                    'secretary': 3,
                    'member': 2,
                    'external': 1,
                }

                user_level = role_levels.get(user_role.level, 0)
                required_level = role_levels.get(self.required_level, 0)

                if user_level >= required_level:
                    return True

        return False


class ModuleContextMixin:
    """
    Mixin que agrega información del módulo al contexto.
    """
    module_code = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.module_code:
            try:
                module = Module.objects.get(code=self.module_code)
                context['current_module'] = {
                    'code': module.code,
                    'name': module.name,
                    'description': module.description,
                    'icon': module.icon,
                    'actions': module.get_available_actions(),
                }

                # Agregar submódulos si es módulo padre
                if module.is_top_level:
                    context['current_module']['submodules'] = [
                        {
                            'code': sub.code,
                            'name': sub.name,
                            'icon': sub.icon,
                            'description': sub.description,
                        }
                        for sub in module.submodules.filter(is_active=True)
                    ]
            except Module.DoesNotExist:
                pass

        return context