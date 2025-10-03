# Sistema ACL (Access Control List) - PyMEMAD

## Descripción General

El sistema ACL de PyMEMAD proporciona un control granular de acceso basado en roles y módulos. Permite gestionar qué usuarios pueden realizar qué acciones en cada parte del sistema.

## Componentes Principales

### 1. Modelos

#### Module
- Define los módulos/apps del sistema
- Soporta jerarquía (módulos padre e hijos)
- Define las acciones disponibles por módulo

#### Role
- Roles del sistema (Super Admin, Admin, Miembro de Junta, etc.)
- Cada rol tiene un nivel jerárquico
- Los roles del sistema no pueden ser eliminados

#### RoleModuleAccess
- Define el acceso de un rol a un módulo específico
- Especifica las acciones habilitadas para ese rol en ese módulo

#### AuditLog
- Registra todos los cambios en permisos
- Útil para auditoría y seguimiento

### 2. Mixins

#### ACLPermissionMixin
```python
from apps.permissions.mixins import ACLPermissionMixin

class MemberListView(ACLPermissionMixin, ListView):
    module_code = 'members'
    required_action = 'view'
    model = Member
```

#### RoleRequiredMixin
```python
class AdminView(RoleRequiredMixin, TemplateView):
    required_roles = ['admin', 'super_admin']
    template_name = 'admin_panel.html'
```

#### BulkActionMixin
Para manejar acciones masivas en vistas de lista.

### 3. Decoradores

#### require_permission
```python
from apps.permissions.decorators import require_permission

@require_permission('billing', 'manage_payments')
def process_payment(request):
    # Solo usuarios con permiso de gestionar pagos
    pass
```

#### require_role
```python
@require_role('treasurer', 'admin')
def financial_report(request):
    # Solo tesoreros y admins
    pass
```

#### ajax_require_permission
```python
@ajax_require_permission('members', 'delete')
def ajax_delete_member(request):
    # Retorna JSON response con error si no tiene permisos
    pass
```

## Configuración Inicial

### 1. Agregar la app a INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ...
    'apps.permissions',
    # ...
]
```

### 2. Agregar context processors

```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ...
                'apps.permissions.context_processors.user_permissions_context',
                'apps.permissions.context_processors.user_quick_info',
                # ...
            ],
        },
    },
]
```

### 3. Incluir URLs

```python
urlpatterns = [
    # ...
    path('permissions/', include('apps.permissions.urls')),
    # ...
]
```

### 4. Ejecutar migraciones

```bash
python manage.py makemigrations permissions
python manage.py makemigrations accounts  # Para los nuevos campos de User
python manage.py migrate
```

### 5. Inicializar el sistema

```bash
python manage.py init_acl
```

Este comando crea:
- Los módulos del sistema
- Los roles por defecto
- Las asignaciones de permisos iniciales

## Uso en Templates

### Verificar permisos

```django
{% if acl_permissions.can_edit %}
    <button>Editar</button>
{% endif %}

{% if acl_permissions.can_delete %}
    <button>Eliminar</button>
{% endif %}
```

### Menú dinámico basado en permisos

```django
{% for module_code, module_info in user_modules.items %}
    {% if module_info.submodules %}
        <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#">
                <i class="{{ module_info.icon }}"></i>
                {{ module_info.name }}
            </a>
            <ul class="dropdown-menu">
                {% for submodule in module_info.submodules %}
                    {% if submodule.url %}
                        <li>
                            <a href="{% url submodule.url %}">
                                {{ submodule.name }}
                            </a>
                        </li>
                    {% endif %}
                {% endfor %}
            </ul>
        </li>
    {% endif %}
{% endfor %}
```

## Roles Predefinidos

### Super Administrador (`super_admin`)
- Acceso completo al sistema
- Puede realizar cualquier acción

### Administrador (`admin`)
- Acceso casi completo
- Gestión general del sistema

### Miembro de Junta (`board_member`)
- Acceso amplio a módulos principales
- Puede aprobar y gestionar decisiones

### Tesorero (`treasurer`)
- Acceso completo a facturación
- Vista de reportes financieros
- Acceso limitado a otros módulos

### Secretario (`secretary`)
- Gestión de documentos y actas
- Comunicaciones
- Gobernanza

### Miembro (`member`)
- Acceso básico de lectura
- Vista de directorio de miembros
- Acceso a documentos públicos

### Externo (`external`)
- Acceso muy limitado
- Solo vista de información pública

## API de Usuario

Los métodos ACL están disponibles en el modelo User:

```python
# Obtener todos los roles del usuario
roles = user.get_all_roles()

# Verificar si tiene un rol específico
if user.has_role('treasurer'):
    # ...

# Verificar permiso en módulo
if user.has_permission_in_module('billing', 'approve'):
    # ...

# Verificar acceso a módulo
if user.can_access_module('members'):
    # ...

# Obtener todos los permisos especiales
permissions = user.get_all_special_permissions()
```

## Acciones Disponibles

Las acciones estándar del sistema incluyen:

### Básicas
- `view`: Ver registros
- `add`: Crear nuevos registros
- `change`: Modificar registros
- `delete`: Eliminar registros

### Gestión de Datos
- `import`: Importar desde Excel/CSV
- `export`: Exportar a Excel/PDF

### Operaciones del Negocio
- `approve`: Aprobar solicitudes
- `reject`: Rechazar solicitudes
- `assign`: Asignar recursos
- `bulk_update`: Actualización masiva
- `manage_members`: Gestionar miembros
- `manage_payments`: Gestionar pagos
- `send_notification`: Enviar notificaciones
- `view_reports`: Ver reportes
- `generate_report`: Generar reportes
- `view_sensitive`: Ver datos sensibles

## Personalización

### Agregar nuevos módulos

```python
from apps.permissions.models import Module

module = Module.objects.create(
    code='custom_module',
    name='Módulo Personalizado',
    app_label='custom',
    description='Mi módulo personalizado',
    icon='fas fa-cog',
    available_actions=['view', 'add', 'change', 'custom_action']
)
```

### Crear roles personalizados

```python
from apps.permissions.models import Role, RoleModuleAccess

role = Role.objects.create(
    code='custom_role',
    name='Rol Personalizado',
    description='Mi rol personalizado',
    level='member'
)

# Asignar permisos
access = RoleModuleAccess.objects.create(
    role=role,
    module=module
)
access.enabled_actions = ['view', 'add']
access.save()
```

### Asignar rol a usuario

```python
from apps.accounts.models import User
from apps.permissions.models import Role

user = User.objects.get(username='usuario')
role = Role.objects.get(code='treasurer')

# Asignar como rol principal
user.primary_role = role
user.save()

# O agregar como rol adicional
user.additional_roles.add(role)
```

## Auditoría

Todos los cambios en permisos se registran automáticamente:

```python
from apps.permissions.models import AuditLog

# Ver últimos cambios de permisos
logs = AuditLog.objects.filter(
    user=user
).order_by('-performed_at')[:10]

for log in logs:
    print(f"{log.action}: {log.details}")
```

## Mejores Prácticas

1. **Siempre usar mixins o decoradores** en las vistas que requieren permisos
2. **No hardcodear roles o permisos** - usar constantes o configuración
3. **Documentar los permisos requeridos** en cada vista/endpoint
4. **Usar el sistema de auditoría** para cambios importantes
5. **Testear permisos** en diferentes escenarios de usuario
6. **Mantener roles simples** - no crear demasiados roles específicos
7. **Usar permisos granulares** cuando sea necesario con `RoleModuleAccess`

## Troubleshooting

### El usuario no puede acceder a un módulo
1. Verificar que el usuario tenga un rol asignado
2. Verificar que el rol tenga permisos en ese módulo
3. Verificar que el módulo esté activo
4. Revisar logs de auditoría

### Los permisos no se reflejan en la interfaz
1. Limpiar caché del navegador
2. Verificar que el context processor esté configurado
3. Verificar que el usuario esté autenticado
4. Revisar la sesión del usuario

### Error "No tiene permisos para realizar esta acción"
1. Verificar el decorador/mixin usado
2. Verificar los permisos del rol
3. Verificar que el usuario tenga el rol correcto
4. Revisar si es superusuario

## Soporte

Para reportar problemas o solicitar nuevas características, contactar al equipo de desarrollo.