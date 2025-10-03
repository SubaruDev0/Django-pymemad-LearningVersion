"""
Template tags y filtros para el sistema de permisos ACL de PyMEMAD.
"""
from django import template
from django.contrib.auth import get_user_model

register = template.Library()
User = get_user_model()


@register.filter
def get_item(dictionary, key):
    """
    Template filter para obtener un item de un diccionario usando una variable como clave.

    Uso: {{ mydict|get_item:mykey }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def has_permission(user, permission_string):
    """
    Verifica si un usuario tiene un permiso específico.

    Uso: {% if user|has_permission:"members.view" %}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Parsear el string del permiso
    parts = permission_string.split('.')
    if len(parts) == 2:
        module_code, action_code = parts
        return user.has_permission_in_module(module_code, action_code)

    return False


@register.filter
def has_role(user, role_code):
    """
    Verifica si un usuario tiene un rol específico.

    Uso: {% if user|has_role:"treasurer" %}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.has_role(role_code)


@register.filter
def has_any_role(user, role_codes):
    """
    Verifica si un usuario tiene alguno de los roles especificados.

    Uso: {% if user|has_any_role:"treasurer,secretary,admin" %}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    roles = role_codes.split(',')
    for role_code in roles:
        if user.has_role(role_code.strip()):
            return True

    return False


@register.filter
def can_access_module(user, module_code):
    """
    Verifica si un usuario puede acceder a un módulo.

    Uso: {% if user|can_access_module:"billing" %}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.can_access_module(module_code)


@register.filter
def get_user_role_name(user):
    """
    Obtiene el nombre del rol principal del usuario.

    Uso: {{ user|get_user_role_name }}
    """
    if not user or not user.is_authenticated:
        return "Sin rol"

    if user.is_superuser:
        return "Super Administrador"

    if user.primary_role:
        return user.primary_role.name

    return "Sin rol asignado"


@register.filter
def get_user_role_badge_class(user):
    """
    Obtiene la clase CSS para el badge del rol del usuario.

    Uso: <span class="badge {{ user|get_user_role_badge_class }}">
    """
    if not user or not user.is_authenticated:
        return "bg-secondary"

    if user.is_superuser:
        return "bg-danger"

    if user.primary_role:
        role_code = user.primary_role.code
        badge_classes = {
            'super_admin': 'bg-danger',
            'admin': 'bg-warning',
            'board_member': 'bg-primary',
            'treasurer': 'bg-success',
            'secretary': 'bg-info',
            'member': 'bg-secondary',
            'external': 'bg-light text-dark'
        }
        return badge_classes.get(role_code, 'bg-secondary')

    return "bg-secondary"


@register.filter
def get_module_actions(module):
    """
    Obtiene las acciones disponibles para un módulo.

    Uso: {% for action in module|get_module_actions %}
    """
    if not module:
        return []

    return module.get_available_actions()


@register.filter
def get_action_display(module, action_code):
    """
    Obtiene el nombre display de una acción para un módulo.

    Uso: {{ module|get_action_display:"view" }}
    """
    if not module:
        return action_code

    return module.get_action_display(action_code)


@register.simple_tag
def user_has_module_permission(user, module_code, action_code):
    """
    Tag para verificar si un usuario tiene un permiso específico en un módulo.

    Uso: {% user_has_module_permission user "members" "approve" as can_approve %}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.has_permission_in_module(module_code, action_code)


@register.inclusion_tag('permissions/tags/role_badge.html')
def role_badge(user):
    """
    Renderiza un badge con el rol del usuario.

    Uso: {% role_badge user %}
    """
    if not user or not user.is_authenticated:
        return {
            'role_name': 'Sin rol',
            'badge_class': 'bg-secondary',
            'icon_class': 'fas fa-user-slash'
        }

    if user.is_superuser:
        return {
            'role_name': 'Super Admin',
            'badge_class': 'bg-danger',
            'icon_class': 'fas fa-crown'
        }

    if user.primary_role:
        role_icons = {
            'super_admin': 'fas fa-crown',
            'admin': 'fas fa-user-shield',
            'board_member': 'fas fa-user-tie',
            'treasurer': 'fas fa-coins',
            'secretary': 'fas fa-file-signature',
            'member': 'fas fa-user',
            'external': 'fas fa-user-clock'
        }

        badge_classes = {
            'super_admin': 'bg-danger',
            'admin': 'bg-warning',
            'board_member': 'bg-primary',
            'treasurer': 'bg-success',
            'secretary': 'bg-info',
            'member': 'bg-secondary',
            'external': 'bg-light text-dark'
        }

        return {
            'role_name': user.primary_role.name,
            'badge_class': badge_classes.get(user.primary_role.code, 'bg-secondary'),
            'icon_class': role_icons.get(user.primary_role.code, 'fas fa-user')
        }

    return {
        'role_name': 'Sin rol asignado',
        'badge_class': 'bg-secondary',
        'icon_class': 'fas fa-user-slash'
    }


@register.inclusion_tag('permissions/tags/permission_check.html')
def permission_check(user, module_code, action_code):
    """
    Renderiza un indicador de permiso (check o X).

    Uso: {% permission_check user "members" "approve" %}
    """
    has_permission = False

    if user and user.is_authenticated:
        if user.is_superuser:
            has_permission = True
        else:
            has_permission = user.has_permission_in_module(module_code, action_code)

    return {
        'has_permission': has_permission
    }


@register.filter
def module_permission_count(user, module_code):
    """
    Cuenta cuántos permisos tiene un usuario en un módulo específico.

    Uso: {{ user|module_permission_count:"billing" }}
    """
    if not user or not user.is_authenticated:
        return 0

    if user.is_superuser:
        return -1  # Indicador de acceso completo

    if not user.primary_role:
        return 0

    from apps.permissions.models import RoleModuleAccess

    try:
        access = RoleModuleAccess.objects.get(
            role=user.primary_role,
            module__code=module_code
        )
        return len(access.enabled_actions) if access.enabled_actions else 0
    except RoleModuleAccess.DoesNotExist:
        return 0


@register.filter
def format_permission_list(permission_list):
    """
    Formatea una lista de permisos para mostrar.

    Uso: {{ enabled_actions|format_permission_list }}
    """
    if not permission_list:
        return "Sin permisos"

    from apps.permissions.constants import STANDARD_ACTIONS

    formatted = []
    for action in permission_list:
        if action in STANDARD_ACTIONS:
            formatted.append(STANDARD_ACTIONS[action]['name'])
        else:
            formatted.append(action.replace('_', ' ').title())

    return ", ".join(formatted)