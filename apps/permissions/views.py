from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import json

from apps.accounts.models import User
from apps.members.models import Company
from .models import (
    Module, ModulePermission, Role, RoleModuleAccess,
    AuditLog
)
from .mixins import ACLPermissionMixin, RoleRequiredMixin
from .decorators import require_permission, require_role
from ..core.models import Person

User = get_user_model()


@login_required
@require_role('admin', 'super_admin')
def permissions_list(request):
    """
    Vista principal para listar usuarios y sus permisos
    """
    # Obtener todos los usuarios con sus permisos
    users = User.objects.select_related('primary_role').prefetch_related(
        'additional_roles'
    ).all()

    # Si es una solicitud API, devolver JSON
    if request.GET.get('api') == 'true':
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name(),
                'primary_role': user.primary_role.name if user.primary_role else None,
                'is_active': user.is_active
            })
        return JsonResponse({'success': True, 'users': users_data})

    # Obtener roles disponibles
    roles = Role.objects.filter(is_active=True).order_by('level', 'name')

    context = {
        'users': users,
        'roles': roles,
        'active_menu': 'permissions',
        'breadcrumbs': [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Permisos', 'url': None},
        ]
    }

    return render(request, 'permissions/permissions_list.html', context)


# @login_required
# @require_role('admin', 'super_admin')
# def user_permissions_detail(request, user_id):
#     """
#     Vista detallada de permisos de un usuario específico
#     """
#     user = get_object_or_404(User, id=user_id)
#
#     # Obtener persona asociada si existe
#     try:
#         person = Person.objects.filter(user=user).first()
#     except Person.DoesNotExist:
#         person = None
#
#     # Obtener módulos con permisos (combinar primary_role y additional_roles)
#     modules_access_dict = {}
#
#     # Obtener todos los roles del usuario
#     all_roles = []
#     if user.primary_role:
#         all_roles.append(user.primary_role)
#     all_roles.extend(user.additional_roles.all())
#
#     # Combinar permisos de todos los roles
#     for role in all_roles:
#         role_module_accesses = RoleModuleAccess.objects.filter(
#             role=role
#         ).select_related('module').prefetch_related('permissions')
#
#         for access in role_module_accesses:
#             module_code = access.module.code
#             enabled_actions = access.enabled_actions if access.enabled_actions else []
#
#             # Si el módulo ya existe, combinar las acciones
#             if module_code in modules_access_dict:
#                 # Combinar acciones (unión de conjuntos)
#                 existing_actions = set(modules_access_dict[module_code]['enabled_actions'])
#                 new_actions = set(enabled_actions)
#                 modules_access_dict[module_code]['enabled_actions'] = list(existing_actions | new_actions)
#             else:
#                 # Crear nueva entrada
#                 modules_access_dict[module_code] = {
#                     'module': access.module,
#                     'permissions': access.permissions.all(),
#                     'enabled_actions': enabled_actions,
#                 }
#
#     # Convertir el diccionario a lista y agregar flags booleanos explícitos
#     modules_access = []
#     for module_code, item in modules_access_dict.items():
#         enabled_actions = item['enabled_actions']
#         modules_access.append({
#             'module': item['module'],
#             'permissions': item['permissions'],
#             'enabled_actions': enabled_actions,
#             'can_view': 'view' in enabled_actions,
#             'can_add': 'add' in enabled_actions,
#             'can_change': 'change' in enabled_actions,
#             'can_delete': 'delete' in enabled_actions,
#         })
#
#     # DEBUG: Imprimir todos los permisos del usuario
#     print("\n" + "="*80)
#     print(f"DEBUG - PERMISOS DEL USUARIO: {user.username} (ID: {user.id})")
#     print("="*80)
#     print(f"Rol Principal: {user.primary_role}")
#     print(f"Roles Adicionales: {list(user.additional_roles.all())}")
#     print(f"\nTotal de módulos con acceso: {len(modules_access)}")
#     print("\nPermisos por módulo:")
#     for item in modules_access:
#         print(f"\n  Módulo: {item['module'].name} (code: {item['module'].code})")
#         print(f"    Acciones habilitadas: {item['enabled_actions']}")
#         print(f"    - can_view: {item['can_view']}")
#         print(f"    - can_add: {item['can_add']}")
#         print(f"    - can_change: {item['can_change']}")
#         print(f"    - can_delete: {item['can_delete']}")
#         special_actions = [a for a in item['enabled_actions'] if a not in ['view', 'add', 'change', 'delete']]
#         if special_actions:
#             print(f"    - Acciones especiales: {special_actions}")
#     print("\n" + "="*80 + "\n")
#
#     # Obtener logs de auditoría recientes
#     audit_logs = AuditLog.objects.filter(
#         user=user
#     ).select_related('performed_by').order_by('-performed_at')[:20]
#
#     # Obtener todos los roles disponibles para el modal de edición
#     roles = Role.objects.filter(is_active=True).order_by('level', 'name')
#
#     context = {
#         'selected_user': user,  # Cambio de nombre para evitar conflicto
#         'person': person,
#         'modules_access': modules_access,
#         'audit_logs': audit_logs,
#         'roles': roles,
#         'active_menu': 'permissions',
#         'breadcrumbs': [
#             {'name': 'Panel', 'url': '/panel/'},
#             {'name': 'Permisos', 'url': '/permissions/users/'},
#             {'name': user.get_full_name() or user.username, 'url': None},
#         ]
#     }
#
#     return render(request, 'permissions/user_permissions_detail.html', context)

@login_required
@require_role('admin', 'super_admin')
def user_permissions_detail(request, user_id):
    """
    Vista detallada de permisos de un usuario específico
    """
    # IMPORTANTE: Cargar el usuario con las relaciones necesarias
    user = get_object_or_404(
        User.objects.select_related('primary_role')
                    .prefetch_related(
                        'primary_role__allowed_regions',
                        'additional_roles',
                        'additional_roles__allowed_regions'
                    ),
        id=user_id
    )

    # Obtener persona asociada si existe
    person = Person.objects.filter(user=user).first()

    # Obtener módulos con permisos (combinar primary_role y additional_roles)
    modules_access_dict = {}

    # Obtener todos los roles del usuario
    all_roles = []
    if user.primary_role:
        all_roles.append(user.primary_role)
    all_roles.extend(user.additional_roles.all())

    # Combinar permisos de todos los roles
    for role in all_roles:
        role_module_accesses = RoleModuleAccess.objects.filter(
            role=role
        ).select_related('module').prefetch_related('permissions')

        for access in role_module_accesses:
            module_code = access.module.code
            enabled_actions = access.enabled_actions if access.enabled_actions else []

            # Si el módulo ya existe, combinar las acciones
            if module_code in modules_access_dict:
                # Combinar acciones (unión de conjuntos)
                existing_actions = set(modules_access_dict[module_code]['enabled_actions'])
                new_actions = set(enabled_actions)
                modules_access_dict[module_code]['enabled_actions'] = list(existing_actions | new_actions)
            else:
                # Crear nueva entrada
                modules_access_dict[module_code] = {
                    'module': access.module,
                    'permissions': list(access.permissions.all()),
                    'enabled_actions': enabled_actions,
                }

    # Convertir el diccionario a lista y agregar flags booleanos explícitos
    modules_access = []
    for module_code, item in modules_access_dict.items():
        enabled_actions = item['enabled_actions']
        modules_access.append({
            'module': item['module'],
            'permissions': item['permissions'],
            'enabled_actions': enabled_actions,
            'can_view': bool('view' in enabled_actions),
            'can_add': bool('add' in enabled_actions),
            'can_change': bool('change' in enabled_actions),
            'can_delete': bool('delete' in enabled_actions),
        })

    # Obtener logs de auditoría recientes
    audit_logs = AuditLog.objects.filter(
        user=user
    ).select_related('performed_by').order_by('-performed_at')[:20]

    # Obtener todos los roles disponibles para el modal de edición
    roles = Role.objects.filter(is_active=True).prefetch_related('allowed_regions').order_by('level', 'name')

    context = {
        'selected_user': user,
        'person': person,
        'modules_access': modules_access,
        'audit_logs': audit_logs,
        'roles': roles,
        'active_menu': 'permissions',
        'breadcrumbs': [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Permisos', 'url': '/permissions/users/'},
            {'name': user.get_full_name() or user.username, 'url': None},
        ]
    }

    return render(request, 'permissions/user_permissions_detail.html', context)

@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def assign_role(request):
    """
    Asignar rol a usuario (AJAX)
    """
    # Manejar tanto JSON como form data
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        role_id = data.get('role_id')
        notes = data.get('notes', '')
    else:
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        notes = request.POST.get('notes', '')

    try:
        user = User.objects.get(id=user_id)

        # Guardar rol anterior para auditoría
        old_role = user.primary_role
        old_additional_roles = list(user.additional_roles.all())

        # Caso especial: role_id vacío significa revocar todos los permisos
        if not role_id or (isinstance(role_id, str) and role_id.strip() == ''):
            # Revocar rol principal
            user.primary_role = None
            user.additional_roles.clear()
            user.save(update_fields=['primary_role'])

            # Limpiar grupos de Django
            user.groups.clear()

            # Crear log de auditoría
            AuditLog.objects.create(
                user=user,
                action='role_removed',
                details={
                    'old_role': old_role.name if old_role else None,
                    'old_additional_roles': [r.name for r in old_additional_roles],
                    'notes': notes or 'Revocación de todos los permisos',
                },
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return JsonResponse({
                'success': True,
                'message': f'Todos los permisos han sido revocados para {user.get_full_name()}'
            })

        # Caso normal: asignar rol específico
        role = Role.objects.get(id=role_id)

        # Asignar nuevo rol
        user.primary_role = role
        user.save(update_fields=['primary_role'])

        # Sincronizar con grupo Django si existe
        if role.django_group:
            user.groups.clear()
            user.groups.add(role.django_group)

        # Crear log de auditoría
        AuditLog.objects.create(
            user=user,
            action='role_assigned',
            details={
                'old_role': old_role.name if old_role else None,
                'new_role': role.name,
                'role_level': role.level,
                'notes': notes,
            },
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse({
            'success': True,
            'message': f'Rol {role.name} asignado correctamente a {user.get_full_name()}'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def toggle_user_status(request):
    """
    Activar/desactivar usuario (AJAX)
    """
    # Manejar JSON o form data
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        user_id = data.get('user_id')
    else:
        user_id = request.POST.get('user_id')

    try:
        user = User.objects.get(id=user_id)

        # Proteger superadmin
        if user.is_superuser:
            return JsonResponse({
                'success': False,
                'message': 'No se puede desactivar a un usuario superadministrador'
            }, status=400)

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])

        # Crear log de auditoría
        AuditLog.objects.create(
            user=user,
            action='user_activated' if user.is_active else 'user_deactivated',
            details={
                'new_status': 'active' if user.is_active else 'inactive'
            },
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f'Usuario {"activado" if user.is_active else "desactivado"} correctamente'
        })

    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Usuario no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def update_module_permissions(request):
    """
    Actualizar permisos de módulo para un rol (AJAX)
    """
    role_id = request.POST.get('role_id')
    module_id = request.POST.get('module_id')
    enabled_actions = request.POST.getlist('actions[]', [])

    try:
        role = Role.objects.get(id=role_id)
        module = Module.objects.get(id=module_id)

        # Actualizar o crear acceso al módulo
        module_access, created = RoleModuleAccess.objects.update_or_create(
            role=role,
            module=module,
            defaults={
                'enabled_actions': enabled_actions
            }
        )

        # Obtener todos los usuarios con este rol y crear logs
        users_with_role = User.objects.filter(
            Q(primary_role=role) | Q(additional_roles=role)
        )

        for user in users_with_role:
            AuditLog.objects.create(
                user=user,
                action='permission_added' if created else 'permission_updated',
                details={
                    'role': role.name,
                    'module': module.name,
                    'actions': enabled_actions
                },
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

        return JsonResponse({
            'success': True,
            'message': f'Permisos del módulo {module.name} actualizados para el rol {role.name}'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_role('admin', 'super_admin')
def roles_management(request):
    """
    Vista para gestión de roles
    """
    roles = Role.objects.all().order_by('level', 'name')

    # Contar usuarios por rol
    for role in roles:
        role.user_count = User.objects.filter(
            Q(primary_role=role) | Q(additional_roles=role)
        ).distinct().count()

    # Contar roles del sistema
    system_roles_count = roles.filter(is_system=True).count()

    # Contar total de usuarios
    total_users = sum(role.user_count for role in roles)

    context = {
        'roles': roles,
        'system_roles_count': system_roles_count,
        'total_users': total_users,
        'active_menu': 'permissions',
        'breadcrumbs': [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Roles', 'url': None},
        ]
    }

    return render(request, 'permissions/roles_management.html', context)


@login_required
@require_role('admin', 'super_admin')
def configure_role_wizard(request, role_id):
    """
    Wizard para configurar permisos de un rol
    """
    role = get_object_or_404(Role, id=role_id)

    # Obtener módulos disponibles organizados jerárquicamente
    parent_modules = Module.objects.filter(
        is_active=True,
        parent=None
    ).order_by('order', 'name').prefetch_related(
        Prefetch('submodules', queryset=Module.objects.filter(is_active=True).order_by('order', 'name'))
    )

    # Obtener permisos actuales del rol
    current_permissions = {}
    role_module_accesses = RoleModuleAccess.objects.filter(role=role)
    for access in role_module_accesses:
        current_permissions[access.module.id] = access.enabled_actions or []

    # Obtener metadatos de acciones desde constants
    from .constants import STANDARD_ACTIONS, get_actions_by_category

    action_metadata = {}
    for action_code, action_info in STANDARD_ACTIONS.items():
        action_metadata[action_code] = {
            'label': action_info['name'],
            'icon': action_info.get('icon', 'fas fa-cog'),
            'description': action_info['description'],
            'category': action_info.get('category', 'basic')
        }

    actions_by_category = get_actions_by_category()

    # Obtener las regiones disponibles
    from apps.core.models import PymeMadRegion
    regions = PymeMadRegion.objects.filter(is_active=True).order_by('name')

    context = {
        'role': role,
        'parent_modules': parent_modules,
        'current_permissions': current_permissions,
        'action_metadata': action_metadata,
        'actions_by_category': actions_by_category,
        'regions': regions,
        'active_menu': 'permissions',
        'breadcrumbs': [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Roles', 'url': '/permissions/roles/'},
            {'name': role.name, 'url': None},
        ]
    }

    return render(request, 'permissions/role_configuration_wizard.html', context)


@login_required
@require_role('admin', 'super_admin')
def modules_management(request):
    """
    Vista para gestión de módulos
    """
    # Obtener módulos organizados jerárquicamente
    parent_modules = Module.objects.filter(
        parent=None
    ).order_by('order', 'name').prefetch_related(
        Prefetch('submodules', queryset=Module.objects.all().order_by('order', 'name'))
    )

    # Calcular total de submódulos
    total_submodules = Module.objects.filter(parent__isnull=False).count()

    # Obtener las acciones disponibles del modelo para pasarlas al template
    action_choices = Module.ACTION_CHOICES

    # Organizar las acciones por categorías para el template
    action_categories = {
        'Básicas': [],
        'Gestión': [],
        'Datos': [],
        'Especiales': [],
        'Auditoría': []
    }

    # Mapeo de iconos para cada acción
    action_icons = {
        'view': 'ai-show',
        'add': 'ai-plus',
        'change': 'ai-edit-alt',
        'delete': 'ai-trash',
        'approve': 'ai-checks',
        'reject': 'ai-cross-alt',
        'assign': 'ai-user-check',
        'transfer': 'ai-shuffle',
        'export': 'ai-download',
        'import': 'ai-upload',
        'backup': 'ai-save',
        'generate_report': 'ai-bar-chart',
        'manage_payments': 'ai-credit-card',
        'view_sensitive': 'ai-eye-off',
        'bulk_update': 'ai-refresh',
        'audit': 'ai-activity',
        'override': 'ai-shield-off',
        'restore': 'ai-refresh-cw'
    }

    # Categorizar las acciones
    for code, name in action_choices:
        action_data = {
            'code': code,
            'name': name,
            'icon': action_icons.get(code, 'ai-circle')
        }

        if code in ['view', 'add', 'change', 'delete']:
            action_categories['Básicas'].append(action_data)
        elif code in ['approve', 'reject', 'assign', 'transfer']:
            action_categories['Gestión'].append(action_data)
        elif code in ['export', 'import', 'backup']:
            action_categories['Datos'].append(action_data)
        elif code in ['generate_report', 'manage_payments', 'view_sensitive', 'bulk_update']:
            action_categories['Especiales'].append(action_data)
        elif code in ['audit', 'override', 'restore']:
            action_categories['Auditoría'].append(action_data)

    context = {
        'parent_modules': parent_modules,
        'total_submodules': total_submodules,
        'action_choices': action_choices,
        'action_categories': action_categories,
        'active_menu': 'permissions',
        'breadcrumbs': [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Módulos', 'url': None},
        ]
    }

    return render(request, 'permissions/modules_management.html', context)


class ModuleCreateView(ACLPermissionMixin, CreateView):
    """
    Vista para crear módulos
    """
    model = Module
    fields = ['code', 'name', 'app_label', 'parent', 'description', 'icon', 'available_actions', 'order']
    template_name = 'permissions/module_form.html'
    success_url = reverse_lazy('permissions:modules_management')
    module_code = 'permissions'
    required_action = 'add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'permissions'
        context['breadcrumbs'] = [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Módulos', 'url': '/permissions/modules/'},
            {'name': 'Crear Módulo', 'url': None},
        ]
        return context


class ModuleUpdateView(ACLPermissionMixin, UpdateView):
    """
    Vista para actualizar módulos
    """
    model = Module
    fields = ['name', 'description', 'icon', 'available_actions', 'order', 'is_active']
    template_name = 'permissions/module_form.html'
    success_url = reverse_lazy('permissions:modules_management')
    module_code = 'permissions'
    required_action = 'change'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'permissions'
        context['breadcrumbs'] = [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Módulos', 'url': '/permissions/modules/'},
            {'name': f'Editar: {self.object.name}', 'url': None},
        ]
        return context


@login_required
@require_role('admin', 'super_admin')
def audit_logs(request):
    """
    Vista para logs de auditoría
    """
    logs = AuditLog.objects.all().select_related(
        'user', 'performed_by'
    ).order_by('-performed_at')[:100]

    context = {
        'logs': logs,
        'active_menu': 'permissions',
        'breadcrumbs': [
            {'name': 'Panel', 'url': '/panel/'},
            {'name': 'Auditoría', 'url': None},
        ]
    }

    return render(request, 'permissions/audit_logs.html', context)


# ============ API VIEWS ============

@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def api_create_role(request):
    """API para crear un nuevo rol"""
    try:
        from apps.permissions.forms import RoleCreationForm
        form = RoleCreationForm(request.POST)

        if form.is_valid():
            role = form.save()
            return JsonResponse({
                'success': True,
                'role_id': role.id,
                'message': f'Rol {role.name} creado exitosamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
def api_get_role_permissions(request, role_id):
    """API para obtener permisos de un rol"""
    try:
        role = get_object_or_404(Role, id=role_id)
        permissions = role.get_all_permissions()

        return JsonResponse({
            'success': True,
            'role': {
                'id': role.id,
                'name': role.name,
                'code': role.code,
                'level': role.level,
                'scope': role.scope,
            },
            'permissions': permissions
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def api_update_role_permissions(request, role_id):
    """API para actualizar permisos de un rol"""
    try:
        role = get_object_or_404(Role, id=role_id)
        data = json.loads(request.body)

        module_code = data.get('module_code')
        actions = data.get('actions', [])

        if not module_code:
            return JsonResponse({
                'success': False,
                'message': 'module_code es requerido'
            }, status=400)

        module = Module.objects.get(code=module_code)
        access, created = RoleModuleAccess.objects.update_or_create(
            role=role,
            module=module,
            defaults={'enabled_actions': actions}
        )

        # Crear log de auditoría
        AuditLog.objects.create(
            user=request.user,
            action='permission_updated',
            details={
                'role': role.name,
                'module': module.name,
                'actions': actions,
                'created': created
            },
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse({
            'success': True,
            'message': f'Permisos actualizados para {module.name}'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def api_configure_role_wizard(request, role_id):
    """API para configuración masiva de rol vía wizard"""
    try:
        role = get_object_or_404(Role, id=role_id)
        data = json.loads(request.body)

        # Actualizar gobernanza del rol
        governance = data.get('governance', 'regional')
        allowed_regions_data = data.get('allowed_regions', [])

        role.governance = governance
        role.save()

        # Si es regional, asignar las regiones permitidas
        if governance == 'regional' and allowed_regions_data:
            from apps.core.models import PymeMadRegion
            # Extraer solo los IDs de la estructura
            region_ids = [int(r['id']) if isinstance(r, dict) else int(r)
                         for r in allowed_regions_data]
            regions = PymeMadRegion.objects.filter(id__in=region_ids)
            role.allowed_regions.set(regions)
        else:
            role.allowed_regions.clear()

        # Procesar permissions_config con la nueva estructura
        permissions_config = data.get('permissions_config', {})

        # Limpiar permisos existentes
        RoleModuleAccess.objects.filter(role=role).delete()

        for module_key, module_data in permissions_config.items():
            try:
                module_code = module_data.get('module_code')
                if not module_code:
                    continue

                module = Module.objects.get(code=module_code)

                # Extraer permisos (acciones habilitadas)
                permissions = module_data.get('permissions', {})
                enabled_actions = [action for action, enabled in permissions.items() if enabled]

                # Extraer scopes por acción
                action_scopes = module_data.get('action_scopes', {})

                # Determinar el scope general del módulo
                # Si todos los scopes son 'all', el módulo tiene scope 'all'
                # Si al menos uno es 'own', el módulo tiene scope 'own'
                module_scope = 'all'
                if action_scopes:
                    if any(scope == 'own' for scope in action_scopes.values()):
                        module_scope = 'own'

                # Crear o actualizar el acceso del rol al módulo
                role_access = RoleModuleAccess.objects.create(
                    role=role,
                    module=module,
                    enabled_actions=enabled_actions,
                    scope=module_scope
                )

                # Guardar los scopes por acción en settings si es necesario
                if action_scopes:
                    role_access.settings['action_scopes'] = action_scopes
                    role_access.save()

            except Module.DoesNotExist:
                continue

        return JsonResponse({
            'success': True,
            'message': f'Configuración del rol {role.name} actualizada'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["GET"])
def api_get_role_configuration(request, role_id):
    """API para obtener la configuración actual de un rol"""
    try:
        role = get_object_or_404(Role, id=role_id)

        # Obtener configuración de permisos
        role_accesses = RoleModuleAccess.objects.filter(role=role).select_related('module')

        permissions_config = {}
        for access in role_accesses:
            module_config = {
                'module_name': access.module.name,
                'module_code': access.module.code,
                'permissions': {},
                'action_scopes': {}
            }

            # Construir el diccionario de permisos (acciones habilitadas)
            for action in access.module.available_actions:
                module_config['permissions'][action] = action in access.enabled_actions

                # Si la acción está habilitada, agregar su scope
                if action in access.enabled_actions:
                    # Por defecto usar el scope del módulo
                    # En el futuro aquí se puede implementar scopes individuales por acción
                    module_config['action_scopes'][action] = access.scope

            permissions_config[str(access.module.id)] = module_config

        # Obtener regiones permitidas
        allowed_regions = []
        if role.governance == 'regional':
            allowed_regions = list(role.allowed_regions.values('id', 'name'))

        return JsonResponse({
            'success': True,
            'configuration': {
                'governance': role.governance,
                'allowed_regions': allowed_regions,
                'permissions_config': permissions_config
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["DELETE"])
def api_delete_role(request, role_id):
    """API para eliminar un rol"""
    try:
        role = get_object_or_404(Role, id=role_id)

        # No permitir eliminar roles del sistema
        if role.is_system:
            return JsonResponse({
                'success': False,
                'message': 'No se pueden eliminar roles del sistema'
            }, status=400)

        # Verificar si hay usuarios con este rol
        users_with_role = User.objects.filter(
            Q(primary_role=role) | Q(additional_roles=role)
        ).count()

        if users_with_role > 0:
            return JsonResponse({
                'success': False,
                'message': f'No se puede eliminar el rol. Hay {users_with_role} usuarios con este rol.'
            }, status=400)

        role_name = role.name
        role.delete()

        return JsonResponse({
            'success': True,
            'message': f'Rol {role_name} eliminado exitosamente'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
def api_get_role_users(request, role_id):
    """API para obtener usuarios con un rol específico"""
    try:
        role = get_object_or_404(Role, id=role_id)

        users = User.objects.filter(
            Q(primary_role=role) | Q(additional_roles=role)
        ).distinct()

        users_data = [{
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'is_primary': user.primary_role == role,
            'is_active': user.is_active,
        } for user in users]

        return JsonResponse({
            'success': True,
            'count': len(users_data),
            'users': users_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST", "DELETE"])
def api_remove_user_role(request, user_id):
    """API para remover rol de un usuario"""
    try:
        user = get_object_or_404(User, id=user_id)
        data = json.loads(request.body) if request.body else {}
        role_id = data.get('role_id')

        if not role_id:
            # Remover rol principal
            old_role = user.primary_role
            user.primary_role = None
            user.save()
            message = f'Rol principal removido de {user.get_full_name()}'
        else:
            # Remover rol específico
            role = get_object_or_404(Role, id=role_id)

            if user.primary_role == role:
                user.primary_role = None
                user.save()
            else:
                user.additional_roles.remove(role)

            message = f'Rol {role.name} removido de {user.get_full_name()}'

        # Crear log de auditoría
        AuditLog.objects.create(
            user=user,
            action='role_removed',
            details={'role_removed': role_id},
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse({
            'success': True,
            'message': message
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def api_create_module(request):
    """API para crear un nuevo módulo"""
    try:
        import json
        from apps.permissions.forms import ModuleForm

        # Manejar tanto JSON como form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        form = ModuleForm(data)

        if form.is_valid():
            module = form.save()
            return JsonResponse({
                'success': True,
                'module_id': module.id,
                'message': f'Módulo {module.name} creado exitosamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
def api_module_detail(request, module_id):
    """API para obtener detalle de un módulo (GET) o actualizarlo (PUT)"""
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'GET':
        try:
            # Obtener roles con acceso
            accesses = RoleModuleAccess.objects.filter(module=module).select_related('role')

            roles_data = [{
                'role_id': access.role.id,
                'role_name': access.role.name,
                'enabled_actions': access.enabled_actions,
                'settings': access.settings,
            } for access in accesses]

            return JsonResponse({
                'success': True,
                'module': {
                    'id': module.id,
                    'code': module.code,
                    'name': module.name,
                    'description': module.description,
                    'available_actions': module.available_actions,
                    'is_active': module.is_active,
                    'parent': module.parent.id if module.parent else None,
                    'app_label': module.app_label,
                    'url_namespace': module.url_namespace,
                    'icon': module.icon,
                    'order': module.order,
                },
                'roles': roles_data
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    elif request.method == 'PUT':
        try:
            import json
            from apps.permissions.forms import ModuleForm

            # Manejar JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            form = ModuleForm(data, instance=module)

            if form.is_valid():
                module = form.save()
                return JsonResponse({
                    'success': True,
                    'module_id': module.id,
                    'message': f'Módulo {module.name} actualizado exitosamente'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    elif request.method == 'DELETE':
        try:
            # No permitir eliminar módulos con submódulos
            if module.submodules.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede eliminar un módulo que tiene submódulos. Elimine primero los submódulos.'
                }, status=400)

            # No permitir eliminar módulos con permisos asignados
            from apps.permissions.models import RoleModuleAccess
            if RoleModuleAccess.objects.filter(module=module).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede eliminar un módulo que tiene permisos asignados a roles.'
                }, status=400)

            module_name = module.name
            module.delete()

            return JsonResponse({
                'success': True,
                'message': f'Módulo {module_name} eliminado exitosamente'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    else:
        return JsonResponse({
            'success': False,
            'message': 'Método no permitido'
        }, status=405)


@login_required
@require_http_methods(['GET'])
def api_modules_list(request):
    """API endpoint para obtener lista de módulos"""
    try:
        # Obtener todos los módulos activos
        modules = Module.objects.filter(is_active=True).select_related('parent')

        # Organizar módulos por jerarquía
        modules_data = []
        parent_modules = modules.filter(parent__isnull=True).order_by('order', 'name')

        for parent in parent_modules:
            parent_data = {
                'id': parent.id,
                'code': parent.code,
                'name': parent.name,
                'icon': parent.icon,
                'available_actions': parent.available_actions,
                'submodules': []
            }

            # Agregar submódulos
            submodules = modules.filter(parent=parent).order_by('order', 'name')
            for submodule in submodules:
                parent_data['submodules'].append({
                    'id': submodule.id,
                    'code': submodule.code,
                    'name': submodule.name,
                    'icon': submodule.icon,
                    'available_actions': submodule.available_actions
                })

            modules_data.append(parent_data)

        return JsonResponse({
            'success': True,
            'modules': modules_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener módulos: {str(e)}'
        }, status=500)


@login_required
@require_role('admin', 'super_admin')
@require_http_methods(["POST"])
def api_create_user(request):
    """
    Vista para crear un nuevo usuario (AJAX)
    """
    try:
        # Parsear datos JSON
        data = json.loads(request.body)

        # Validar campos requeridos
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'El campo {field} es obligatorio'
                }, status=400)

        # Verificar que el username no exista
        if User.objects.filter(username=data.get('username')).exists():
            return JsonResponse({
                'success': False,
                'message': 'El nombre de usuario ya existe'
            }, status=400)

        # Verificar que el email no exista
        if User.objects.filter(email=data.get('email')).exists():
            return JsonResponse({
                'success': False,
                'message': 'El correo electrónico ya está registrado'
            }, status=400)

        # Crear el usuario
        user = User.objects.create(
            username=data.get('username'),
            email=data.get('email'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_active=data.get('is_active', True),
            is_superuser=data.get('is_superuser', False),
            is_staff=data.get('is_superuser', False)  # Si es superuser, también es staff
        )

        # Establecer la contraseña
        user.set_password(data.get('password'))
        user.save()

        # Asignar rol principal si se especificó
        if data.get('primary_role'):
            try:
                role = Role.objects.get(id=data.get('primary_role'))
                user.primary_role = role
                user.save()
            except Role.DoesNotExist:
                pass  # Ignorar si el rol no existe

        # Crear log de auditoría
        AuditLog.objects.create(
            user=user,
            action='user_created',
            details={
                'created_by': request.user.username,
                'username': user.username,
                'email': user.email,
                'role': user.primary_role.name if user.primary_role else 'Sin rol',
                'is_superuser': user.is_superuser
            },
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse({
            'success': True,
            'message': f'Usuario {user.username} creado correctamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Datos JSON inválidos'
        }, status=400)

    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'message': f'Error de integridad: {str(e)}'
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al crear usuario: {str(e)}'
        }, status=500)
