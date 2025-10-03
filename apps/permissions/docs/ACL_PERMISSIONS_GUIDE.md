# Guía de Permisos ACL - PyMEMAD

## Descripción General
Este documento describe cómo funcionan los permisos ACL en PyMEMAD, específicamente en los módulos de gestión asociativa.

## Permisos por Módulo

### Módulo Miembros (`members`)

#### Permisos Básicos
- **`can_view`**: Permite ver la lista de miembros
- **`can_create`**: Permite crear nuevos miembros
- **`can_edit`**: Permite editar información de miembros existentes
- **`can_delete`**: Permite eliminar miembros

#### Permisos de Importación/Exportación
- **`can_import`**: Permite importar miembros desde Excel
- **`can_export`**: Permite exportar datos de miembros

#### Permisos Administrativos
- **`can_approve`**: Permite aprobar solicitudes de membresía
- **`can_reject`**: Permite rechazar solicitudes de membresía

#### Permisos de Acciones Masivas
- **`can_bulk_update`**: Controla TODAS las acciones masivas:
  - Envío masivo de invitaciones
  - Actualización masiva de estados
  - Asignación masiva de categorías
  - Muestra los checkboxes de selección múltiple
  - Muestra la barra de acciones masivas

#### Permisos Específicos
- **`can_send_invitation`**: Permite enviar invitaciones a nuevos miembros

### Módulo Facturación (`billing`)

#### Permisos Básicos
- **`can_view`**: Permite ver facturas y transacciones
- **`can_create`**: Permite crear nuevas facturas
- **`can_edit`**: Permite editar facturas existentes
- **`can_delete`**: Permite eliminar facturas

#### Permisos Financieros
- **`can_pay`**: Permite registrar pagos
- **`can_reconcile`**: Permite conciliar cuentas bancarias
- **`can_generate_invoice`**: Permite generar facturas automáticas

#### Permisos de Comunicación
- **`can_send_reminder`**: Permite enviar recordatorios de pago

#### Permisos de Exportación
- **`can_export`**: Permite exportar reportes financieros

### Módulo Gobernanza (`governance`)

#### Permisos Básicos
- **`can_view`**: Permite ver actas y documentos
- **`can_create`**: Permite crear nuevas actas
- **`can_edit`**: Permite editar actas y documentos
- **`can_delete`**: Permite eliminar documentos

#### Permisos Administrativos
- **`can_approve`**: Permite aprobar actas oficiales
- **`can_archive`**: Permite archivar documentos

#### Permisos Específicos
- **`can_vote`**: Permite registrar votaciones
- **`can_publish`**: Permite publicar documentos oficiales

### Módulo Eventos (`events`)

#### Permisos Básicos
- **`can_view`**: Permite ver eventos
- **`can_create`**: Permite crear nuevos eventos
- **`can_edit`**: Permite editar eventos existentes
- **`can_delete`**: Permite cancelar eventos

#### Permisos de Gestión
- **`can_assign`**: Permite asignar participantes
- **`can_manage_attendance`**: Permite gestionar asistencia
- **`can_send_notification`**: Permite enviar notificaciones de eventos

## Implementación en Templates

### Template de Lista de Miembros
```django
<!-- members/member_list.html -->

<!-- Solo mostrar checkboxes si tiene permisos de bulk_update o delete -->
{% if acl_permissions.can_bulk_update or acl_permissions.can_delete %}
<th>
    <input type="checkbox" id="select-all" class="form-check-input">
</th>
{% endif %}

<!-- Botón de nuevo miembro -->
{% if acl_permissions.can_create %}
<a href="{% url 'members:create' %}" class="btn btn-primary">
    <i class="fas fa-plus"></i> Nuevo Miembro
</a>
{% endif %}

<!-- Acciones masivas -->
{% if acl_permissions.can_bulk_update %}
<div class="bulk-actions" style="display:none;">
    <button onclick="bulkInvite()" class="btn btn-info">
        <i class="fas fa-envelope"></i> Invitar Seleccionados
    </button>
    <button onclick="bulkUpdateStatus()" class="btn btn-warning">
        <i class="fas fa-sync"></i> Actualizar Estado
    </button>
</div>
{% endif %}

<!-- Aprobar/Rechazar solicitudes -->
{% if acl_permissions.can_approve %}
<button onclick="approveRequest({{ member.id }})" class="btn btn-sm btn-success">
    <i class="fas fa-check"></i> Aprobar
</button>
{% endif %}

{% if acl_permissions.can_reject %}
<button onclick="rejectRequest({{ member.id }})" class="btn btn-sm btn-danger">
    <i class="fas fa-times"></i> Rechazar
</button>
{% endif %}

<!-- Importar/Exportar -->
{% if acl_permissions.can_import %}
<button onclick="openImportModal()" class="btn btn-secondary">
    <i class="fas fa-file-import"></i> Importar desde Excel
</button>
{% endif %}

{% if acl_permissions.can_export %}
<button onclick="exportToExcel()" class="btn btn-secondary">
    <i class="fas fa-file-export"></i> Exportar a Excel
</button>
{% endif %}
```

### Template de Facturación
```django
<!-- billing/invoice_list.html -->

<!-- Generar factura -->
{% if acl_permissions.can_generate_invoice %}
<button onclick="generateInvoice()" class="btn btn-success">
    <i class="fas fa-file-invoice"></i> Generar Factura
</button>
{% endif %}

<!-- Registrar pago -->
{% if acl_permissions.can_pay %}
<button onclick="registerPayment({{ invoice.id }})" class="btn btn-primary">
    <i class="fas fa-credit-card"></i> Registrar Pago
</button>
{% endif %}

<!-- Conciliar cuentas -->
{% if acl_permissions.can_reconcile %}
<button onclick="openReconcileModal()" class="btn btn-warning">
    <i class="fas fa-balance-scale"></i> Conciliar Cuentas
</button>
{% endif %}

<!-- Enviar recordatorio -->
{% if acl_permissions.can_send_reminder %}
<button onclick="sendReminder({{ invoice.id }})" class="btn btn-info">
    <i class="fas fa-bell"></i> Enviar Recordatorio
</button>
{% endif %}
```

## Configuración de Roles

### Rol: Tesorero (Treasurer)
```python
{
    'billing': ['view', 'add', 'change', 'export', 'pay', 'reconcile', 'generate_invoice', 'send_reminder'],
    'members': ['view', 'export'],
    'events': ['view'],
}
```

### Rol: Secretario (Secretary)
```python
{
    'members': ['view', 'add', 'change', 'import', 'export', 'approve', 'reject', 'send_invitation'],
    'governance': ['view', 'add', 'change', 'approve', 'archive', 'publish'],
    'events': ['view', 'add', 'change', 'manage_attendance'],
}
```

### Rol: Directivo (Board Member)
```python
{
    'members': ['view', 'export'],
    'billing': ['view', 'export'],
    'governance': ['view', 'add', 'change', 'approve', 'vote', 'publish'],
    'events': ['view', 'add', 'change', 'assign', 'manage_attendance', 'send_notification'],
}
```

### Rol: Miembro (Member)
```python
{
    'members': ['view'],
    'events': ['view'],
    'governance': ['view', 'vote'],
}
```

## Notas Importantes

1. **Separación de Responsabilidades**:
   - `can_bulk_update` es exclusivo para acciones masivas
   - `can_assign` es para asignaciones individuales
   - Los permisos financieros (`pay`, `reconcile`) están separados para mayor control

2. **Checkboxes de Selección**:
   - Solo aparecen si el usuario tiene `can_bulk_update` o `can_delete`
   - Sin estos permisos, la columna de checkboxes no se muestra

3. **Barra de Acciones Masivas**:
   - Solo visible cuando hay elementos seleccionados
   - Requiere permiso `can_bulk_update` para acciones masivas
   - Requiere permiso `can_delete` para eliminar seleccionados

4. **Permisos Financieros**:
   - Separados por función: `pay`, `reconcile`, `generate_invoice`
   - Permite control granular sobre operaciones financieras
   - El tesorero típicamente tiene todos estos permisos

5. **Permisos de Aprobación**:
   - `can_approve` y `can_reject` son independientes
   - Un usuario puede tener uno sin el otro
   - Útil para flujos de trabajo con múltiples niveles de aprobación

## Ejemplo de Implementación en Vista

```python
# apps/members/views.py

class MemberListView(ACLPermissionMixin, ListView):
    model = Member
    template_name = 'members/member_list.html'
    module_code = 'members'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Los permisos ya están disponibles gracias a ACLPermissionMixin
        # Se acceden en el template como: acl_permissions.can_create, etc.

        # Agregar estadísticas si tiene permiso de vista
        if self.acl_permissions.get('can_view', False):
            context['total_members'] = Member.objects.filter(is_active=True).count()
            context['pending_approvals'] = Member.objects.filter(status='pending').count()

        return context

    def get_queryset(self):
        queryset = super().get_queryset()

        # Si solo tiene permiso de vista, filtrar datos sensibles
        if not self.acl_permissions.get('can_edit', False):
            queryset = queryset.defer('financial_data', 'personal_notes')

        return queryset
```

## Configuración mediante Comando de Gestión

```python
# management/commands/setup_permissions.py

from django.core.management.base import BaseCommand
from apps.permissions.models import Role, Module, RoleModuleAccess

class Command(BaseCommand):
    help = 'Configura los permisos para todos los roles'

    def handle(self, *args, **options):
        # Configurar permisos del Tesorero
        treasurer = Role.objects.get(code='treasurer')
        billing_module = Module.objects.get(code='billing')

        RoleModuleAccess.objects.update_or_create(
            role=treasurer,
            module=billing_module,
            defaults={
                'has_access': True,
                'enabled_actions': [
                    'view', 'add', 'change', 'export',
                    'pay', 'reconcile', 'generate_invoice', 'send_reminder'
                ]
            }
        )

        # Configurar permisos del Secretario
        secretary = Role.objects.get(code='secretary')
        members_module = Module.objects.get(code='members')

        RoleModuleAccess.objects.update_or_create(
            role=secretary,
            module=members_module,
            defaults={
                'has_access': True,
                'enabled_actions': [
                    'view', 'add', 'change', 'import', 'export',
                    'approve', 'reject', 'send_invitation'
                ]
            }
        )

        self.stdout.write(self.style.SUCCESS('Permisos configurados exitosamente'))
```

## Validación de Permisos en API

```python
# apps/members/api_views.py

from rest_framework.decorators import api_view
from apps.permissions.decorators import ajax_require_permission

@api_view(['POST'])
@ajax_require_permission('members', 'approve')
def approve_member_request(request, member_id):
    """
    API endpoint para aprobar solicitudes de membresía
    Requiere permiso 'approve' en el módulo 'members'
    """
    member = get_object_or_404(Member, id=member_id, status='pending')
    member.status = 'approved'
    member.approved_by = request.user
    member.approved_at = timezone.now()
    member.save()

    return JsonResponse({
        'success': True,
        'message': f'Miembro {member.get_full_name()} aprobado correctamente'
    })

@api_view(['POST'])
@ajax_require_permission('billing', 'pay')
def register_payment(request, invoice_id):
    """
    API endpoint para registrar pagos
    Requiere permiso 'pay' en el módulo 'billing'
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    amount = request.data.get('amount')
    payment_method = request.data.get('payment_method')

    payment = Payment.objects.create(
        invoice=invoice,
        amount=amount,
        payment_method=payment_method,
        registered_by=request.user
    )

    return JsonResponse({
        'success': True,
        'payment_id': payment.id,
        'message': 'Pago registrado correctamente'
    })
```

## Conclusión

Este sistema de permisos ACL para PyMEMAD proporciona:
- **Control granular**: Permisos específicos para cada operación
- **Flexibilidad**: Fácil de extender con nuevos módulos y acciones
- **Seguridad**: Validación en múltiples niveles (vistas, API, templates)
- **Trazabilidad**: Registro de auditoría para todas las operaciones
- **Orientación asociativa**: Diseñado específicamente para gestión de asociaciones