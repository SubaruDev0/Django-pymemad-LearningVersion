from django.conf import settings
from django.urls import reverse, NoReverseMatch
from apps.permissions.models import Module, RoleModuleAccess


def user_permissions_context(request):
    """
    Context processor que agrega información de permisos y menús del usuario al contexto
    """
    context = {
        'user_modules': [],  # Lista con módulos y permisos estructurados para sidebar
        'user_roles': [],
        'user_permissions': {},
    }

    if not request.user.is_authenticated:
        return context

    user = request.user
    current_url_name = request.resolver_match.url_name if request.resolver_match else None
    current_namespace = request.resolver_match.namespace if request.resolver_match else None

    # Obtener todos los roles del usuario
    user_roles = []
    if hasattr(user, 'primary_role') and user.primary_role:
        user_roles.append(user.primary_role)
    if hasattr(user, 'additional_roles'):
        user_roles.extend(user.additional_roles.all())

    context['user_roles'] = user_roles

    # Mapeo de códigos de módulo a URLs de PyMEMAD
    url_mapping = {
        # Dashboard
        'dashboard': 'dashboard:dashboard',

        # Miembros
        'members': '#',
        'members_list': 'dashboard:members',
        'members_directory': 'dashboard:members',
        'members_import': 'dashboard:members',

        # Finanzas
        'finance': '#',
        'billing': 'dashboard:billing',
        'expenses': 'dashboard:expenses',
        'balance': 'dashboard:balance',

        # Estrategia
        'strategy': '#',
        'plan': 'dashboard:plan',

        # Contenido
        'content': '#',
        'posts': 'dashboard:post-list',
        'categories': 'dashboard:category-list',
        'tags': 'dashboard:tag-list',

        # Administración
        'administration': '#',
        'contacts': 'dashboard:contact-list',

        # Configuración
        'configuration': '#',
        'users': 'permissions:permissions_list',
        'permissions': 'permissions:modules_management',
        'roles': 'permissions:roles_management',
        'audit': 'permissions:audit_logs',
    }

    # Mapeo de categorías
    category_mapping = {
        'panel': 'Panel Principal',
        'members': 'Gestión',
        'finance': 'Finanzas',
        'strategy': 'Estrategia',
        'content': 'Contenido',
        'administration': 'Administración',
        'configuration': 'Configuración',
    }

    # Si es superusuario, mostrar todos los módulos activos
    if user.is_superuser:
        return _get_superuser_modules(current_url_name, current_namespace, url_mapping, category_mapping)

    # Para usuarios normales, construir menú basado en sus roles
    modules_by_category = {}
    processed_modules = set()

    for role in user_roles:
        # Obtener accesos a módulos para este rol
        module_accesses = RoleModuleAccess.objects.filter(
            role=role,
            module__is_active=True
        ).select_related('module').order_by('module__order', 'module__name')

        for access in module_accesses:
            module = access.module

            # Verificar si tiene permisos habilitados
            if not access.enabled_actions or 'view' not in access.enabled_actions:
                continue

            # Evitar procesar el mismo módulo varias veces
            if module.id in processed_modules:
                continue
            processed_modules.add(module.id)

            # Determinar categoría basada en el código del módulo o su padre
            # Intentar mapear por código del módulo
            category = 'General'
            if module.code in ['dashboard', 'members']:
                category = 'Panel Principal'
            elif module.code in ['billing', 'expenses', 'balance', 'finance']:
                category = 'Finanzas'
            elif module.code in ['plan', 'strategy']:
                category = 'Estrategia'
            elif module.code in ['posts', 'content', 'categories', 'tags']:
                category = 'Contenido'
            elif module.code in ['contacts', 'administration']:
                category = 'Administración'
            elif module.code in ['users', 'permissions', 'roles', 'audit', 'configuration']:
                category = 'Configuración'

            if category not in modules_by_category:
                modules_by_category[category] = []

            # Crear entrada del módulo
            module_entry = {
                'code': module.code,
                'name': module.name,
                'icon': module.icon or 'ai-folder',
                'url': url_mapping.get(module.code, '#'),
                'is_parent': False,
                'is_active': False,
                'is_expanded': False,
                'visible': True,
                'category': category,
                'submodules': []
            }

            # Verificar si el módulo está activo
            if module_entry['url'] and module_entry['url'] != '#':
                try:
                    if current_namespace and ':' in module_entry['url']:
                        namespace, name = module_entry['url'].split(':')
                        module_entry['is_active'] = (current_namespace == namespace and current_url_name == name)
                    else:
                        module_entry['is_active'] = (current_url_name == module_entry['url'])
                except:
                    pass

            # Si tiene módulos hijos, procesarlos
            if module.parent is None:
                child_modules = Module.objects.filter(
                    parent=module,
                    is_active=True
                ).order_by('order', 'name')

                if child_modules.exists():
                    module_entry['is_parent'] = True

                    for child in child_modules:
                        # Verificar si el usuario tiene acceso al submódulo
                        child_access = RoleModuleAccess.objects.filter(
                            role__in=user_roles,
                            module=child
                        ).first()

                        if child_access and child_access.enabled_actions and 'view' in child_access.enabled_actions:
                            child_entry = {
                                'code': child.code,
                                'name': child.name,
                                'icon': child.icon or 'ai-circle',
                                'url': url_mapping.get(child.code, '#'),
                                'is_active': False,
                                'visible': True
                            }

                            # Verificar si el submódulo está activo
                            if child_entry['url'] and child_entry['url'] != '#':
                                try:
                                    if current_namespace and ':' in child_entry['url']:
                                        namespace, name = child_entry['url'].split(':')
                                        child_entry['is_active'] = (current_namespace == namespace and current_url_name == name)
                                    else:
                                        child_entry['is_active'] = (current_url_name == child_entry['url'])
                                except:
                                    pass

                            # Si algún hijo está activo, expandir el padre
                            if child_entry['is_active']:
                                module_entry['is_expanded'] = True
                                module_entry['is_active'] = True

                            module_entry['submodules'].append(child_entry)

            # Solo agregar si no es un módulo hijo (los hijos se agregan como submodules)
            if module.parent is None:
                modules_by_category[category].append(module_entry)

    # Convertir a lista ordenada por categoría
    category_order = ['Panel Principal', 'Gestión', 'Finanzas', 'Estrategia', 'Contenido', 'Administración', 'Configuración']

    for category in category_order:
        if category in modules_by_category:
            for module in modules_by_category[category]:
                context['user_modules'].append(module)

    # Agregar categorías no predefinidas
    for category, modules in modules_by_category.items():
        if category not in category_order:
            for module in modules:
                context['user_modules'].append(module)

    return context


def _get_superuser_modules(current_url_name, current_namespace, url_mapping, category_mapping):
    """
    Obtiene todos los módulos disponibles para superusuarios
    """
    context = {
        'user_modules': [],
        'user_roles': ['Superusuario'],
        'user_permissions': {'all': True},
    }

    # Estructura estática para superusuarios (todos los módulos disponibles)
    modules = [
        # Panel Principal
        {
            'code': 'dashboard',
            'name': 'Dashboard',
            'icon': 'ai-home',
            'url': 'dashboard:dashboard',
            'category': 'Panel Principal',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },
        {
            'code': 'members',
            'name': 'Socios',
            'icon': 'ai-user-group',
            'url': 'dashboard:members',
            'category': 'Panel Principal',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },

        # Finanzas
        {
            'code': 'billing',
            'name': 'Facturación',
            'icon': 'ai-file-text',
            'url': 'dashboard:billing',
            'category': 'Finanzas',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },
        {
            'code': 'expenses',
            'name': 'Gastos y Egresos',
            'icon': 'ai-circle-arrow-down',
            'url': 'dashboard:expenses',
            'category': 'Finanzas',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },
        {
            'code': 'balance',
            'name': 'Balance y Estados',
            'icon': 'ai-bar-chart-1',
            'url': 'dashboard:balance',
            'category': 'Finanzas',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },

        # Estrategia
        {
            'code': 'plan',
            'name': 'Plan Estratégico',
            'icon': 'ai-trending-up',
            'url': 'dashboard:plan',
            'category': 'Estrategia',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },

        # Contenido
        {
            'code': 'content',
            'name': 'Noticias',
            'icon': 'ai-file-text',
            'url': '#',
            'category': 'Contenido',
            'is_parent': True,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': [
                {
                    'code': 'posts',
                    'name': 'Ver Todas',
                    'icon': 'ai-list',
                    'url': 'dashboard:post-list',
                    'is_active': False,
                    'visible': True
                },
                {
                    'code': 'categories',
                    'name': 'Categorías',
                    'icon': 'ai-folder-plus',
                    'url': 'dashboard:category-list',
                    'is_active': False,
                    'visible': True
                },
                {
                    'code': 'tags',
                    'name': 'Etiquetas',
                    'icon': 'ai-tag',
                    'url': 'dashboard:tag-list',
                    'is_active': False,
                    'visible': True
                }
            ]
        },

        # Administración
        {
            'code': 'contacts',
            'name': 'Contactos',
            'icon': 'ai-mail',
            'url': 'dashboard:contact-list',
            'category': 'Administración',
            'is_parent': False,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': []
        },

        # Configuración
        {
            'code': 'configuration',
            'name': 'Gestión de Usuarios',
            'icon': 'ai-user-check',
            'url': '#',
            'category': 'Configuración',
            'is_parent': True,
            'is_active': False,
            'is_expanded': False,
            'visible': True,
            'submodules': [
                {
                    'code': 'users',
                    'name': 'Usuarios del Sistema',
                    'icon': 'ai-user',
                    'url': 'permissions:permissions_list',
                    'is_active': False,
                    'visible': True
                },
                {
                    'code': 'permissions',
                    'name': 'Permisos',
                    'icon': 'ai-shield',
                    'url': 'permissions:modules_management',
                    'is_active': False,
                    'visible': True
                },
                {
                    'code': 'roles',
                    'name': 'Roles',
                    'icon': 'ai-award',
                    'url': 'permissions:roles_management',
                    'is_active': False,
                    'visible': True
                },
                {
                    'code': 'audit',
                    'name': 'Auditoría',
                    'icon': 'ai-activity',
                    'url': 'permissions:audit_logs',
                    'is_active': False,
                    'visible': True
                }
            ]
        }
    ]

    # Actualizar estado activo
    for module in modules:
        # Verificar módulo principal
        if module['url'] and module['url'] != '#':
            try:
                if ':' in module['url']:
                    namespace, name = module['url'].split(':')
                    module['is_active'] = (current_namespace == namespace and current_url_name == name)
            except:
                pass

        # Verificar submódulos
        for submodule in module.get('submodules', []):
            if submodule['url'] and submodule['url'] != '#':
                try:
                    if ':' in submodule['url']:
                        namespace, name = submodule['url'].split(':')
                        submodule['is_active'] = (current_namespace == namespace and current_url_name == name)

                        # Si el submódulo está activo, expandir el padre
                        if submodule['is_active']:
                            module['is_expanded'] = True
                            module['is_active'] = True
                except:
                    pass

    context['user_modules'] = modules
    return context


def user_quick_info(request):
    """
    Context processor minimalista para información rápida del usuario
    """
    if not request.user.is_authenticated:
        return {
            'quick_user_info': {
                'is_authenticated': False,
                'is_admin': False,
                'has_any_role': False,
            }
        }

    user = request.user
    return {
        'quick_user_info': {
            'is_authenticated': True,
            'is_admin': user.is_superuser or user.groups.filter(name='admin').exists(),
            'has_any_role': bool(hasattr(user, 'primary_role') and user.primary_role) or
                           (hasattr(user, 'additional_roles') and user.additional_roles.exists()),
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
        }
    }