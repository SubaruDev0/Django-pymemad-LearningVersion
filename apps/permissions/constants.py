"""
Constantes y configuración estándar para el sistema de permisos ACL.
"""

# Scopes (alcances) para permisos granulares
PERMISSION_SCOPES = {
    'all': 'Todos los registros',
    'own': 'Solo registros propios',
    'group': 'Solo registros del grupo',
    'association': 'Solo registros de la asociación',
}

# Acciones estándar disponibles en el sistema
STANDARD_ACTIONS = {
    # Acciones Básicas (CRUD)
    'view': {
        'name': 'Ver',
        'description': 'Ver listado y detalles de registros',
        'category': 'basic',
        'icon': 'ni ni-bullet-list-67'
    },
    'add': {
        'name': 'Crear',
        'description': 'Crear nuevos registros',
        'category': 'basic',
        'icon': 'ni ni-fat-add'
    },
    'change': {
        'name': 'Editar',
        'description': 'Modificar registros existentes',
        'category': 'basic',
        'icon': 'ni ni-settings-gear-65'
    },
    'delete': {
        'name': 'Eliminar',
        'description': 'Eliminar registros',
        'category': 'basic',
        'icon': 'ni ni-fat-remove'
    },

    # Gestión de Datos
    'import': {
        'name': 'Importar',
        'description': 'Importar datos desde archivos Excel/CSV',
        'category': 'data',
        'icon': 'ni ni-cloud-upload-96'
    },
    'export': {
        'name': 'Exportar',
        'description': 'Exportar datos a Excel/PDF',
        'category': 'data',
        'icon': 'ni ni-cloud-download-95'
    },

    # Operaciones del Negocio
    'assign': {
        'name': 'Asignar',
        'description': 'Asignar recursos o responsabilidades',
        'category': 'business',
        'icon': 'ni ni-send'
    },
    'approve': {
        'name': 'Aprobar',
        'description': 'Aprobar solicitudes o registros',
        'category': 'business',
        'icon': 'ni ni-check-bold'
    },
    'reject': {
        'name': 'Rechazar',
        'description': 'Rechazar solicitudes o registros',
        'category': 'business',
        'icon': 'ni ni-fat-remove'
    },
    'bulk_update': {
        'name': 'Actualización Masiva',
        'description': 'Realizar cambios en múltiples registros',
        'category': 'business',
        'icon': 'ni ni-collection'
    },

    # Acciones específicas de PyMEMAD
    'manage_members': {
        'name': 'Gestionar Miembros',
        'description': 'Administrar altas, bajas y modificaciones de miembros',
        'category': 'business',
        'icon': 'ni ni-single-02'
    },
    'manage_payments': {
        'name': 'Gestionar Pagos',
        'description': 'Administrar pagos, cuotas y facturación',
        'category': 'business',
        'icon': 'ni ni-money-coins'
    },
    'send_notification': {
        'name': 'Enviar Notificaciones',
        'description': 'Enviar notificaciones por email o SMS',
        'category': 'business',
        'icon': 'ni ni-email-83'
    },
    'view_reports': {
        'name': 'Ver Reportes',
        'description': 'Acceder a reportes y estadísticas',
        'category': 'business',
        'icon': 'ni ni-chart-bar-32'
    },
    'generate_report': {
        'name': 'Generar Reportes',
        'description': 'Crear nuevos reportes personalizados',
        'category': 'business',
        'icon': 'ni ni-chart-pie-35'
    },
    'view_sensitive': {
        'name': 'Ver Datos Sensibles',
        'description': 'Ver información confidencial de miembros',
        'category': 'business',
        'icon': 'ni ni-lock-circle-open'
    },
}

# Mapeo de categorías a nombres más amigables
ACTION_CATEGORIES = {
    'basic': 'Acciones Básicas',
    'data': 'Gestión de Datos',
    'business': 'Operaciones del Negocio',
}

# Función auxiliar para obtener acciones organizadas por categorías
def get_actions_by_category():
    """Organiza las acciones por categorías para mostrar en formularios"""
    categorized_actions = {}

    for action_code, action_info in STANDARD_ACTIONS.items():
        category = action_info.get('category', 'basic')
        category_name = ACTION_CATEGORIES.get(category, 'Otras')

        if category_name not in categorized_actions:
            categorized_actions[category_name] = []

        categorized_actions[category_name].append((
            action_code,
            action_info['name'],
            action_info['description']
        ))

    # Ordenar las categorías para consistencia
    ordered_categories = {}
    for cat in ['Acciones Básicas', 'Gestión de Datos', 'Operaciones del Negocio']:
        if cat in categorized_actions:
            ordered_categories[cat] = categorized_actions[cat]

    # Agregar cualquier categoría adicional que pueda existir
    for cat, actions in categorized_actions.items():
        if cat not in ordered_categories:
            ordered_categories[cat] = actions

    return ordered_categories

# Configuración de acciones por módulo específico de PyMEMAD
MODULE_ACTIONS = {
    'members': {
        'name': 'Miembros',
        'actions': ['view', 'add', 'change', 'delete', 'import', 'export', 'manage_members', 'view_sensitive', 'bulk_update']
    },
    'billing': {
        'name': 'Facturación',
        'actions': ['view', 'add', 'change', 'delete', 'manage_payments', 'export', 'approve', 'send_notification']
    },
    'governance': {
        'name': 'Gobernanza',
        'actions': ['view', 'add', 'change', 'delete', 'approve', 'reject', 'assign', 'export']
    },
    'communications': {
        'name': 'Comunicaciones',
        'actions': ['view', 'add', 'change', 'delete', 'send_notification', 'bulk_update']
    },
    'documents': {
        'name': 'Documentos',
        'actions': ['view', 'add', 'change', 'delete', 'export', 'approve']
    },
    'news': {
        'name': 'Noticias',
        'actions': ['view', 'add', 'change', 'delete', 'approve', 'reject']
    },
    'strategy': {
        'name': 'Estrategia',
        'actions': ['view', 'add', 'change', 'delete', 'view_reports', 'generate_report', 'export']
    },
    'panel': {
        'name': 'Panel de Control',
        'actions': ['view', 'view_reports', 'generate_report', 'export']
    }
}

def get_module_actions(module_code):
    """
    Obtiene las acciones disponibles para un módulo específico.

    Args:
        module_code (str): Código del módulo

    Returns:
        list: Lista de acciones disponibles para el módulo
    """
    module_config = MODULE_ACTIONS.get(module_code, {})
    return module_config.get('actions', [])

def get_action_info(action_code):
    """
    Obtiene la información de una acción específica.

    Args:
        action_code (str): Código de la acción

    Returns:
        dict: Información de la acción
    """
    return STANDARD_ACTIONS.get(action_code, {})

def validate_action(module_code, action_code):
    """
    Valida si una acción es válida para un módulo.

    Args:
        module_code (str): Código del módulo
        action_code (str): Código de la acción

    Returns:
        bool: True si la acción es válida para el módulo
    """
    module_actions = get_module_actions(module_code)
    return action_code in module_actions