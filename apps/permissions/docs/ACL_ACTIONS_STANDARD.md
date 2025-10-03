# Estándar de Acciones ACL - Sistema de Permisos PyMEMAD

## Introducción
Este documento define el estándar de acciones (`enabled_actions`) que se deben usar consistentemente en todo el sistema ACL de PyMEMAD.

## Acciones Estándar

### Acciones CRUD Básicas
- **`view`**: Permite ver/listar registros
- **`add`**: Permite crear/agregar nuevos registros
- **`change`**: Permite editar/modificar registros existentes
- **`delete`**: Permite eliminar registros

### Acciones de Datos
- **`import`**: Permite importar datos desde archivos externos (Excel, CSV, etc.)
- **`export`**: Permite exportar datos a archivos externos

### Acciones de Gestión
- **`assign`**: Permite asignar recursos o relaciones
- **`bulk_update`**: Permite realizar actualizaciones masivas sobre múltiples registros

### Acciones Administrativas
- **`approve`**: Permite aprobar solicitudes o documentos
- **`reject`**: Permite rechazar solicitudes o documentos
- **`archive`**: Permite archivar registros

### Acciones Financieras
- **`pay`**: Permite registrar pagos
- **`reconcile`**: Permite conciliar cuentas
- **`generate_invoice`**: Permite generar facturas

### Acciones Específicas por Módulo

#### Módulo Miembros (`members`)
```json
{
  "enabled_actions": [
    "view",              // Ver lista de miembros
    "add",               // Agregar nuevos miembros
    "change",            // Editar información de miembros
    "delete",            // Eliminar miembros
    "import",            // Importar miembros desde Excel
    "export",            // Exportar lista de miembros
    "approve",           // Aprobar solicitudes de membresía
    "reject",            // Rechazar solicitudes
    "bulk_update",       // Actualización masiva de miembros
    "send_invitation"    // Enviar invitaciones (específico del módulo)
  ]
}
```

#### Módulo Facturación (`billing`)
```json
{
  "enabled_actions": [
    "view",              // Ver facturas y pagos
    "add",               // Crear nuevas facturas
    "change",            // Editar facturas
    "delete",            // Eliminar facturas
    "export",            // Exportar reportes financieros
    "pay",               // Registrar pagos
    "reconcile",         // Conciliar cuentas
    "generate_invoice",  // Generar facturas automáticas
    "send_reminder"      // Enviar recordatorios de pago (específico del módulo)
  ]
}
```

#### Módulo Gobernanza (`governance`)
```json
{
  "enabled_actions": [
    "view",              // Ver actas y documentos
    "add",               // Crear nuevas actas
    "change",            // Editar actas
    "delete",            // Eliminar actas
    "export",            // Exportar documentos
    "approve",           // Aprobar actas
    "archive",           // Archivar documentos
    "vote",              // Registrar votaciones (específico del módulo)
    "publish"            // Publicar documentos oficiales (específico del módulo)
  ]
}
```

#### Módulo Eventos (`events`)
```json
{
  "enabled_actions": [
    "view",              // Ver eventos
    "add",               // Crear nuevos eventos
    "change",            // Editar eventos
    "delete",            // Eliminar eventos
    "export",            // Exportar calendario
    "assign",            // Asignar participantes
    "bulk_update",       // Actualización masiva
    "manage_attendance", // Gestionar asistencia (específico del módulo)
    "send_notification"  // Enviar notificaciones (específico del módulo)
  ]
}
```

## Mapeo de Acciones a Permisos en Vistas

### Patrón Estándar de Mapeo

```python
# En el método get_acl_permissions() de las vistas

action_mapping = {
    # CRUD básico
    'view': 'can_view',
    'add': 'can_create',
    'change': 'can_edit',
    'delete': 'can_delete',

    # Datos
    'import': 'can_import',
    'export': 'can_export',

    # Gestión
    'assign': 'can_assign',
    'bulk_update': 'can_bulk_update',

    # Administrativas
    'approve': 'can_approve',
    'reject': 'can_reject',
    'archive': 'can_archive',

    # Financieras
    'pay': 'can_pay',
    'reconcile': 'can_reconcile',
    'generate_invoice': 'can_generate_invoice',

    # Específicas del módulo
    'send_invitation': 'can_send_invitation',      # members
    'send_reminder': 'can_send_reminder',          # billing
    'vote': 'can_vote',                            # governance
    'publish': 'can_publish',                      # governance
    'manage_attendance': 'can_manage_attendance',  # events
    'send_notification': 'can_send_notification',  # events
}
```

### Implementación en Vistas

```python
def get_acl_permissions(self):
    """
    Obtiene los permisos específicos del usuario para el módulo.
    """
    from apps.permissions.models import Role, Module, RoleModuleAccess

    # Inicializar permisos con valores por defecto
    permissions = {
        'can_view': False,
        'can_create': False,
        'can_edit': False,
        'can_delete': False,
        'can_assign': False,
        'can_import': False,
        'can_export': False,
        'can_bulk_update': False,
        'can_approve': False,
        'can_reject': False,
        'can_archive': False,
        'can_pay': False,
        'can_reconcile': False,
        'can_generate_invoice': False,
    }

    # ... lógica para obtener enabled_actions ...

    # Mapear acciones a permisos
    for action in enabled_actions:
        permission_key = f'can_{action}'
        if permission_key in permissions:
            permissions[permission_key] = True
        # Manejar acciones específicas del módulo
        elif action == 'send_invitation':
            permissions['can_send_invitation'] = True
        elif action == 'send_reminder':
            permissions['can_send_reminder'] = True
        elif action == 'vote':
            permissions['can_vote'] = True
        elif action == 'publish':
            permissions['can_publish'] = True
        elif action == 'manage_attendance':
            permissions['can_manage_attendance'] = True
        elif action == 'send_notification':
            permissions['can_send_notification'] = True

    return permissions
```

## Uso en Templates

### Control de Visibilidad de Elementos

```django
<!-- Botón de crear -->
{% if acl_permissions.can_create %}
<a href="{% url 'members:create' %}" class="btn btn-primary">
    <i class="fas fa-plus"></i> Nuevo Miembro
</a>
{% endif %}

<!-- Acciones masivas -->
{% if acl_permissions.can_bulk_update %}
<div class="bulk-actions">
    <button onclick="bulkInvite()" class="btn btn-info">
        <i class="fas fa-envelope"></i> Invitar Seleccionados
    </button>
</div>
{% endif %}

<!-- Aprobar/Rechazar -->
{% if acl_permissions.can_approve %}
<button onclick="approveRequest()" class="btn btn-success">
    <i class="fas fa-check"></i> Aprobar
</button>
{% endif %}

{% if acl_permissions.can_reject %}
<button onclick="rejectRequest()" class="btn btn-danger">
    <i class="fas fa-times"></i> Rechazar
</button>
{% endif %}

<!-- Importar/Exportar -->
{% if acl_permissions.can_import %}
<button onclick="importData()" class="btn btn-secondary">
    <i class="fas fa-file-import"></i> Importar
</button>
{% endif %}

{% if acl_permissions.can_export %}
<button onclick="exportData()" class="btn btn-secondary">
    <i class="fas fa-file-export"></i> Exportar
</button>
{% endif %}
```

## Configuración en Base de Datos

### Tabla `permissions_rolemoduleaccess`

```sql
-- Ejemplo de configuración para tesorero con permisos financieros
INSERT INTO permissions_rolemoduleaccess (role_id, module_id, has_access, enabled_actions)
VALUES (
    4,  -- role_id (treasurer)
    2,  -- module_id (billing)
    true,
    '["view", "add", "change", "export", "pay", "reconcile", "generate_invoice", "send_reminder"]'::jsonb
);

-- Ejemplo de configuración para miembro regular
INSERT INTO permissions_rolemoduleaccess (role_id, module_id, has_access, enabled_actions)
VALUES (
    6,  -- role_id (member)
    1,  -- module_id (members)
    true,
    '["view", "export"]'::jsonb
);
```

## Comandos de Gestión

Para cargar módulos con sus acciones disponibles:

```python
# En management/commands/init_acl.py

Module.objects.update_or_create(
    code='members',
    defaults={
        'name': 'Gestión de Miembros',
        'available_actions': [
            'view', 'add', 'change', 'delete',
            'import', 'export', 'approve', 'reject',
            'bulk_update', 'send_invitation'
        ],
        # ... otros campos
    }
)

Module.objects.update_or_create(
    code='billing',
    defaults={
        'name': 'Facturación',
        'available_actions': [
            'view', 'add', 'change', 'delete',
            'export', 'pay', 'reconcile',
            'generate_invoice', 'send_reminder'
        ],
        # ... otros campos
    }
)
```

## Roles Predefinidos de PyMEMAD

### 1. Super Admin
- Acceso completo a todos los módulos
- Todas las acciones habilitadas

### 2. Admin
- Acceso completo a módulos operativos
- Restricciones en configuración del sistema

### 3. Board Member (Directivo)
- Acceso a gobernanza, eventos y reportes
- Puede aprobar documentos y gestionar eventos

### 4. Treasurer (Tesorero)
- Acceso completo a facturación
- Puede generar reportes financieros
- Gestión de pagos y conciliación

### 5. Secretary (Secretario)
- Gestión de miembros y documentación
- Puede aprobar solicitudes de membresía
- Gestión de actas y documentos

### 6. Member (Miembro)
- Acceso de solo lectura a la mayoría de módulos
- Puede actualizar su propia información
- Puede participar en votaciones

### 7. External (Externo)
- Acceso muy limitado
- Solo visualización de información pública

## Reglas y Mejores Prácticas

1. **Consistencia**: Siempre usar los mismos códigos de acción en todos los módulos
2. **Documentación**: Documentar cualquier acción específica del módulo
3. **Mapeo claro**: Mantener un mapeo 1:1 entre acciones y permisos
4. **No inventar**: No crear nuevas acciones sin documentarlas aquí primero
5. **Compatibilidad**: Mantener compatibilidad con el sistema existente
6. **Contexto asociativo**: Las acciones deben reflejar operaciones típicas de asociaciones

## Migración de Datos Existentes

Si necesitas actualizar los `enabled_actions` existentes:

```python
from apps.permissions.models import RoleModuleAccess

# Actualizar todas las entradas del módulo members
RoleModuleAccess.objects.filter(
    module__code='members'
).update(
    enabled_actions=['view', 'add', 'change', 'delete', 'import', 'export', 'approve', 'reject', 'bulk_update', 'send_invitation']
)

# Actualizar permisos del tesorero
RoleModuleAccess.objects.filter(
    role__code='treasurer',
    module__code='billing'
).update(
    enabled_actions=['view', 'add', 'change', 'export', 'pay', 'reconcile', 'generate_invoice', 'send_reminder']
)
```

## Validación

Para validar que los enabled_actions son correctos:

```python
def validate_enabled_actions(module_code, actions):
    """
    Valida que las acciones sean válidas para el módulo.
    """
    STANDARD_ACTIONS = [
        'view', 'add', 'change', 'delete',
        'import', 'export', 'assign', 'bulk_update',
        'approve', 'reject', 'archive',
        'pay', 'reconcile', 'generate_invoice'
    ]

    MODULE_SPECIFIC_ACTIONS = {
        'members': ['send_invitation'],
        'billing': ['send_reminder'],
        'governance': ['vote', 'publish'],
        'events': ['manage_attendance', 'send_notification'],
        # Agregar más módulos según sea necesario
    }

    valid_actions = STANDARD_ACTIONS.copy()
    if module_code in MODULE_SPECIFIC_ACTIONS:
        valid_actions.extend(MODULE_SPECIFIC_ACTIONS[module_code])

    invalid_actions = [a for a in actions if a not in valid_actions]
    if invalid_actions:
        raise ValueError(f"Acciones inválidas para {module_code}: {invalid_actions}")

    return True
```

## Conclusión

Este estándar asegura que el sistema de permisos ACL de PyMEMAD sea:
- **Consistente**: Las mismas acciones significan lo mismo en todos los módulos
- **Mantenible**: Fácil de entender y modificar
- **Escalable**: Fácil agregar nuevos módulos siguiendo el mismo patrón
- **Documentado**: Claro para todos los desarrolladores del equipo
- **Orientado a asociaciones**: Refleja las necesidades específicas de gestión asociativa