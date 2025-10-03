"""
Decoradores para el sistema de permisos ACL.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def require_permission(module_code, action_code):
    """
    Decorador que requiere un permiso específico para acceder a una vista.

    Uso:
        @require_permission('members', 'view')
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return func(request, *args, **kwargs)

            # Verificar permiso
            if not request.user.has_permission_in_module(module_code, action_code):
                messages.error(request, "No tiene permisos para realizar esta acción.")
                raise PermissionDenied("No tiene permisos para realizar esta acción.")

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*role_codes):
    """
    Decorador que requiere que el usuario tenga uno de los roles especificados.

    Uso:
        @require_role('admin', 'board_member')
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return func(request, *args, **kwargs)

            # Verificar si tiene alguno de los roles
            for role_code in role_codes:
                if request.user.has_role(role_code):
                    return func(request, *args, **kwargs)

            messages.error(request, "No tiene el rol necesario para acceder a esta sección.")
            raise PermissionDenied("No tiene el rol necesario para acceder a esta sección.")
        return wrapper
    return decorator


def require_module_access(module_code):
    """
    Decorador que requiere acceso a un módulo específico.

    Uso:
        @require_module_access('members')
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return func(request, *args, **kwargs)

            # Verificar acceso al módulo
            if not request.user.can_access_module(module_code):
                messages.error(request, f"No tiene acceso al módulo {module_code}.")
                raise PermissionDenied(f"No tiene acceso al módulo {module_code}.")

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def ajax_require_permission(module_code, action_code):
    """
    Decorador para vistas AJAX que requiere un permiso específico.

    Uso:
        @ajax_require_permission('members', 'delete')
        def ajax_delete_member(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from django.http import JsonResponse

            # Verificar autenticación
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'message': 'Debe iniciar sesión para realizar esta acción.'
                }, status=401)

            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return func(request, *args, **kwargs)

            # Verificar permiso
            if not request.user.has_permission_in_module(module_code, action_code):
                return JsonResponse({
                    'success': False,
                    'message': 'No tiene permisos para realizar esta acción.'
                }, status=403)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required_or_403(module_code, action_code):
    """
    Decorador similar a require_permission pero sin redirección.
    Lanza PermissionDenied directamente.

    Uso:
        @permission_required_or_403('billing', 'manage_payments')
        def process_payment(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser or request.user.has_permission_in_module(module_code, action_code):
                return func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return decorator


def require_special_permission(permission_key):
    """
    Decorador para verificar permisos especiales.
    Formato: módulo.acción o módulo.categoría.acción

    Uso:
        @require_special_permission('billing.reconcile')
        def reconcile_accounts(request):
            ...

        @require_special_permission('governance.vote')
        def cast_vote(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Parsear el permission_key
            parts = permission_key.split('.')
            if len(parts) == 2:
                module_code, action_code = parts
                if request.user.has_permission_in_module(module_code, action_code):
                    return view_func(request, *args, **kwargs)

            # Obtener nombre del permiso para mensaje más claro
            try:
                from apps.permissions.models import Module
                if len(parts) == 2:
                    module_code, action_code = parts
                    module = Module.objects.get(code=module_code)
                    perm_name = f"{module.name}: {module.get_action_display(action_code)}"
                else:
                    perm_name = permission_key
            except:
                perm_name = permission_key

            messages.error(
                request,
                f'No tienes permiso para: {perm_name}'
            )

            # Si es AJAX, retornar 403
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponseForbidden(f'Permiso requerido: {perm_name}')

            # Sino, redirigir al dashboard
            return redirect('panel:index')

        return wrapper
    return decorator


def require_any_permission(*permission_keys):
    """
    Decorador para verificar que el usuario tenga AL MENOS UNO de los permisos.

    Uso:
        @require_any_permission('members.view', 'members.add')
        def members_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            for permission_key in permission_keys:
                parts = permission_key.split('.')
                if len(parts) == 2:
                    module_code, action_code = parts
                    if request.user.has_permission_in_module(module_code, action_code):
                        return view_func(request, *args, **kwargs)

            messages.error(
                request,
                'No tienes los permisos necesarios para acceder a esta sección'
            )

            return redirect('panel:index')

        return wrapper
    return decorator


def require_all_permissions(*permission_keys):
    """
    Decorador para verificar que el usuario tenga TODOS los permisos.

    Uso:
        @require_all_permissions('billing.pay', 'billing.reconcile')
        def complete_financial_operation(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Superusuarios siempre tienen acceso
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            missing_perms = []
            for permission_key in permission_keys:
                parts = permission_key.split('.')
                if len(parts) == 2:
                    module_code, action_code = parts
                    if not request.user.has_permission_in_module(module_code, action_code):
                        try:
                            from apps.permissions.models import Module
                            module = Module.objects.get(code=module_code)
                            perm_name = f"{module.name}: {module.get_action_display(action_code)}"
                            missing_perms.append(perm_name)
                        except:
                            missing_perms.append(permission_key)

            if missing_perms:
                messages.error(
                    request,
                    f'Te faltan los siguientes permisos: {", ".join(missing_perms)}'
                )
                return redirect('panel:index')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# Decoradores para roles específicos de PyMEMAD

def admin_required(view_func):
    """Requiere rol de administrador."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if request.user.is_superuser or request.user.has_role('admin') or request.user.has_role('super_admin'):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para administradores')
        raise PermissionDenied('Acceso solo para administradores')

    return wrapper


def board_member_required(view_func):
    """Requiere rol de directivo o superior."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        allowed_roles = ['super_admin', 'admin', 'board_member']
        if request.user.is_superuser or any(request.user.has_role(role) for role in allowed_roles):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para directivos')
        raise PermissionDenied('Acceso solo para directivos')

    return wrapper


def treasurer_required(view_func):
    """Requiere rol de tesorero o superior."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        allowed_roles = ['super_admin', 'admin', 'treasurer']
        if request.user.is_superuser or any(request.user.has_role(role) for role in allowed_roles):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para tesorería')
        raise PermissionDenied('Acceso solo para tesorería')

    return wrapper


def secretary_required(view_func):
    """Requiere rol de secretario o superior."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        allowed_roles = ['super_admin', 'admin', 'secretary']
        if request.user.is_superuser or any(request.user.has_role(role) for role in allowed_roles):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para secretaría')
        raise PermissionDenied('Acceso solo para secretaría')

    return wrapper


def member_required(view_func):
    """Requiere ser miembro activo de la asociación."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        # Cualquier rol excepto 'external' es considerado miembro
        excluded_roles = ['external']
        if request.user.is_superuser or (request.user.primary_role and request.user.primary_role.code not in excluded_roles):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para miembros de la asociación')
        raise PermissionDenied('Acceso solo para miembros')

    return wrapper


# ========== DECORADORES CON SCOPE REGIONAL ==========

def require_national_access(view_func):
    """Requiere acceso nacional para acceder a la vista."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if request.user.has_national_access():
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Esta sección requiere permisos nacionales')
        raise PermissionDenied('Acceso solo para nivel nacional')

    return wrapper


def require_regional_access(region_param='region_id'):
    """
    Requiere acceso a una región específica.

    Uso:
        @require_regional_access()  # Busca region_id en kwargs
        def view(request, region_id):
            ...

        @require_regional_access('custom_region_id')  # Usa parámetro personalizado
        def view(request, custom_region_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Obtener el ID de la región del parámetro
            region_id = kwargs.get(region_param)

            if not region_id:
                # Si no hay región específica, verificar acceso general
                if request.user.has_regional_access():
                    return view_func(request, *args, **kwargs)
            else:
                # Verificar acceso a la región específica
                if request.user.has_regional_access(region_id):
                    return view_func(request, *args, **kwargs)

            messages.error(request, 'No tienes acceso a esta región')
            raise PermissionDenied('Sin acceso regional')

        return wrapper
    return decorator


def require_permission_with_scope(module_code, action_code, scope_param='region_id'):
    """
    Decorador que verifica permisos considerando el scope regional.

    Uso:
        @require_permission_with_scope('members', 'approve')
        def approve_member(request, region_id, member_id):
            # Solo usuarios con permiso 'approve' en 'members'
            # Y acceso a la región especificada
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Verificar permiso básico
            if not request.user.has_permission_in_module(module_code, action_code):
                messages.error(request, f"No tienes permiso para {action_code} en {module_code}")
                raise PermissionDenied

            # Verificar scope si se proporciona región
            region_id = kwargs.get(scope_param)
            if region_id:
                if not request.user.has_regional_access(region_id):
                    messages.error(request, 'No tienes acceso a esta región')
                    raise PermissionDenied

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_hierarchy_level(max_level):
    """
    Requiere un nivel jerárquico máximo para acceder.

    Uso:
        @require_hierarchy_level(20)  # Solo presidentes y superiores
        def sensitive_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            user_level = request.user.get_hierarchy_level()
            if user_level <= max_level:
                return view_func(request, *args, **kwargs)

            messages.error(request, 'No tienes el nivel jerárquico necesario')
            raise PermissionDenied('Nivel jerárquico insuficiente')

        return wrapper
    return decorator


def can_manage_user_required(user_param='user_id'):
    """
    Verifica que el usuario actual puede gestionar al usuario objetivo.

    Uso:
        @can_manage_user_required()
        def edit_user(request, user_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Obtener el usuario objetivo
            user_id = kwargs.get(user_param)
            if user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    target_user = User.objects.get(id=user_id)
                    if not request.user.can_manage_user(target_user):
                        messages.error(request, 'No puedes gestionar este usuario')
                        raise PermissionDenied('Sin permisos para gestionar este usuario')
                except User.DoesNotExist:
                    raise PermissionDenied('Usuario no encontrado')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Decoradores específicos para roles de gobernanza

def national_president_required(view_func):
    """Requiere rol de presidente nacional o superior."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        allowed_roles = ['super_admin', 'admin', 'national_president']
        if request.user.is_superuser or any(request.user.has_role(role) for role in allowed_roles):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para Presidencia Nacional')
        raise PermissionDenied('Acceso solo para Presidencia Nacional')

    return wrapper


def regional_president_required(view_func):
    """Requiere rol de presidente regional o superior."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        allowed_roles = [
            'super_admin', 'admin',
            'national_president', 'national_vice_president',
            'regional_president'
        ]
        if request.user.is_superuser or any(request.user.has_role(role) for role in allowed_roles):
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Acceso solo para Presidencia Regional o superior')
        raise PermissionDenied('Acceso solo para Presidencia Regional o superior')

    return wrapper