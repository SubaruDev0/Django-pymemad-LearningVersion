"""
Ejemplo de permisos granulares para PyMEMAD
Muestra cómo el sistema de permisos ACL maneja diferentes escenarios y roles
"""

from django.db import models
from django.contrib.auth.decorators import login_required
from functools import wraps


class GranularPermissionsExample:
    """
    Configuración de permisos granulares para diferentes roles en PyMEMAD
    Casos: Tesorero vs Miembro regular
    """

    @staticmethod
    def configuracion_tesorero():
        """
        Configuración para un tesorero de la asociación
        """
        return {
            "rol": "treasurer",
            "nivel": "Tesorero",

            # Configuración en el sistema
            "RoleModuleAccess": {
                "modules": {
                    "billing": {
                        "enabled_actions": [
                            "view",           # Ver todas las facturas
                            "add",            # Crear facturas
                            "change",         # Modificar facturas
                            "delete",         # Eliminar facturas (con restricciones)
                            "manage_payments", # Gestionar pagos
                            "export",         # Exportar reportes
                            "approve"         # Aprobar transacciones
                        ]
                    },
                    "members": {
                        "enabled_actions": [
                            "view",           # Ver miembros
                            "export",         # Exportar listados
                            "view_sensitive"  # Ver datos financieros de miembros
                        ]
                    },
                    "panel": {
                        "enabled_actions": [
                            "view",           # Ver dashboard
                            "view_reports",   # Ver reportes financieros
                            "generate_report" # Generar reportes personalizados
                        ]
                    }
                }
            },

            # Métodos de verificación
            "permission_checks": """
                # Verificar si puede aprobar pago
                def can_approve_payment(self, payment):
                    # Tesoreros pueden aprobar todos los pagos
                    return True

                # Verificar si puede ver información financiera
                def can_view_financial_info(self, member):
                    # Tesoreros ven toda la información financiera
                    return True

                # Verificar si puede generar reporte
                def can_generate_financial_report(self):
                    return True

                # Verificar si puede eliminar factura
                def can_delete_invoice(self, invoice):
                    # Solo facturas no pagadas y del mes actual
                    from django.utils import timezone
                    current_month = timezone.now().month
                    return (not invoice.is_paid and
                            invoice.created_at.month == current_month)
            """
        }

    @staticmethod
    def configuracion_miembro():
        """
        Configuración para un miembro regular de la asociación
        """
        return {
            "rol": "member",
            "nivel": "Miembro",

            # Configuración en el sistema
            "RoleModuleAccess": {
                "modules": {
                    "members": {
                        "enabled_actions": [
                            "view",           # Ver directorio de miembros
                        ]
                    },
                    "billing": {
                        "enabled_actions": [
                            "view",           # Ver SUS facturas
                        ]
                    },
                    "documents": {
                        "enabled_actions": [
                            "view",           # Ver documentos públicos
                        ]
                    },
                    "news": {
                        "enabled_actions": [
                            "view",           # Ver noticias
                        ]
                    },
                    "panel": {
                        "enabled_actions": [
                            "view",           # Ver su dashboard personal
                        ]
                    }
                }
            },

            # Restricciones específicas
            "restrictions": {
                "billing": {
                    "scope": "own",  # Solo ve SUS propias facturas
                },
                "documents": {
                    "scope": "public",  # Solo documentos públicos
                },
                "members": {
                    "fields_hidden": ["phone", "email", "address"],  # Datos ocultos
                }
            },

            # Métodos de verificación
            "permission_checks": """
                # Verificar si puede ver factura
                def can_view_invoice(self, invoice):
                    # Solo sus propias facturas
                    return invoice.member.user == self

                # Verificar si puede ver documento
                def can_view_document(self, document):
                    # Solo documentos públicos o propios
                    return document.is_public or document.owner == self

                # Verificar si puede ver información de miembro
                def can_view_member_details(self, member):
                    # Ve información básica, no datos sensibles
                    return True  # Pero con campos limitados
            """
        }

    @staticmethod
    def configuracion_junta_directiva():
        """
        Configuración para un miembro de la junta directiva
        """
        return {
            "rol": "board_member",
            "nivel": "Miembro de Junta",

            # Configuración en el sistema
            "RoleModuleAccess": {
                "modules": {
                    "governance": {
                        "enabled_actions": [
                            "view",           # Ver reuniones y actas
                            "add",            # Crear reuniones
                            "change",         # Modificar actas
                            "delete",         # Eliminar borradores
                            "approve",        # Aprobar decisiones
                            "assign",         # Asignar tareas
                        ]
                    },
                    "members": {
                        "enabled_actions": [
                            "view",           # Ver todos los miembros
                            "add",            # Agregar nuevos miembros
                            "change",         # Modificar información
                            "export",         # Exportar listados
                            "manage_members", # Gestión completa
                        ]
                    },
                    "communications": {
                        "enabled_actions": [
                            "view",           # Ver comunicaciones
                            "add",            # Crear comunicados
                            "send_notification", # Enviar notificaciones
                        ]
                    },
                    "strategy": {
                        "enabled_actions": [
                            "view",           # Ver plan estratégico
                            "add",            # Crear objetivos
                            "change",         # Modificar estrategias
                            "view_reports",   # Ver reportes de avance
                        ]
                    }
                }
            }
        }

    @staticmethod
    def comparacion_permisos():
        """
        Tabla comparativa de permisos entre roles
        """
        return {
            "headers": ["Permiso", "Miembro", "Tesorero", "Junta Directiva"],
            "rows": [
                ["Ver miembros", "✅ Básico", "✅ Completo", "✅ Completo"],
                ["Gestionar miembros", "❌ No", "❌ No", "✅ Sí"],
                ["Ver facturas", "🔒 Propias", "✅ Todas", "✅ Todas"],
                ["Crear facturas", "❌ No", "✅ Sí", "❌ No"],
                ["Aprobar pagos", "❌ No", "✅ Sí", "❌ No"],
                ["Ver documentos", "🔒 Públicos", "✅ Todos", "✅ Todos"],
                ["Crear reuniones", "❌ No", "❌ No", "✅ Sí"],
                ["Enviar comunicados", "❌ No", "❌ No", "✅ Sí"],
                ["Ver reportes financieros", "❌ No", "✅ Sí", "✅ Sí"],
                ["Planificación estratégica", "❌ No", "❌ No", "✅ Sí"],
            ]
        }


# ==============================================================================
# IMPLEMENTACIÓN EN EL MODELO USER
# ==============================================================================

class AssociationPermissionMixin:
    """
    Mixin para agregar al modelo User
    Maneja permisos específicos de asociaciones
    """

    def get_visible_invoices(self):
        """
        Obtiene facturas visibles según rol
        """
        from apps.billing.models import Invoice

        # Si es tesorero o junta, ve todas las facturas
        if self.has_role('treasurer') or self.has_role('board_member'):
            return Invoice.objects.all()

        # Si es miembro, solo sus facturas
        if self.has_role('member'):
            return Invoice.objects.filter(member__user=self)

        # Sin permisos
        return Invoice.objects.none()

    def can_approve_payment(self, payment=None):
        """
        Verifica si puede aprobar pagos
        """
        # Solo tesoreros pueden aprobar pagos
        return self.has_role('treasurer')

    def can_manage_members(self):
        """
        Verifica si puede gestionar miembros
        """
        # Solo junta directiva puede gestionar miembros completamente
        return self.has_role('board_member') or self.has_role('admin')

    def can_send_communications(self):
        """
        Verifica si puede enviar comunicaciones masivas
        """
        # Junta directiva y secretarios pueden enviar comunicaciones
        return self.has_role('board_member') or self.has_role('secretary')

    def can_view_sensitive_data(self, member=None):
        """
        Verifica si puede ver datos sensibles de miembros
        """
        # Tesoreros ven datos financieros
        if self.has_role('treasurer'):
            return True

        # Junta directiva ve todos los datos
        if self.has_role('board_member'):
            return True

        # Miembros solo ven sus propios datos
        if member and member.user == self:
            return True

        return False

    def get_dashboard_widgets(self):
        """
        Obtiene los widgets del dashboard según permisos
        """
        widgets = []

        # Widgets básicos para todos
        widgets.append('profile_summary')
        widgets.append('upcoming_events')

        # Widgets para tesorero
        if self.has_role('treasurer'):
            widgets.extend([
                'financial_summary',
                'pending_payments',
                'income_chart',
                'expense_chart'
            ])

        # Widgets para junta directiva
        if self.has_role('board_member'):
            widgets.extend([
                'member_statistics',
                'pending_approvals',
                'meeting_schedule',
                'strategic_goals'
            ])

        # Widgets para secretario
        if self.has_role('secretary'):
            widgets.extend([
                'pending_documents',
                'communication_queue',
                'meeting_minutes'
            ])

        return widgets


# ==============================================================================
# DECORADORES PARA VISTAS
# ==============================================================================

def treasurer_required(func):
    """
    Decorador que requiere rol de tesorero

    @treasurer_required
    def approve_payment(request, payment_id):
        # Solo tesoreros pueden aprobar pagos
    """
    @wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_role('treasurer'):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden(
                "Solo el tesorero puede realizar esta acción."
            )
        return func(request, *args, **kwargs)
    return wrapper


def board_member_required(func):
    """
    Decorador que requiere ser miembro de junta directiva

    @board_member_required
    def create_meeting(request):
        # Solo junta directiva puede crear reuniones
    """
    @wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_role('board_member'):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden(
                "Solo los miembros de la junta directiva pueden realizar esta acción."
            )
        return func(request, *args, **kwargs)
    return wrapper


def own_resource_or_permission(permission):
    """
    Decorador que permite acceso al propio recurso o con permiso específico

    @own_resource_or_permission('billing.view_all_invoices')
    def view_invoice(request, invoice_id):
        # Miembros ven sus facturas, tesoreros ven todas
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Obtener el recurso (ej: invoice)
            resource_id = kwargs.get('pk') or kwargs.get('id')

            # Si tiene el permiso general, permitir
            if request.user.has_permission_in_module(permission.split('.')[0], permission.split('.')[1]):
                return view_func(request, *args, **kwargs)

            # Verificar si es su propio recurso
            # (Esta lógica debe personalizarse según el recurso)
            from apps.billing.models import Invoice
            if 'invoice' in str(view_func.__name__).lower():
                try:
                    invoice = Invoice.objects.get(pk=resource_id)
                    if invoice.member.user == request.user:
                        return view_func(request, *args, **kwargs)
                except Invoice.DoesNotExist:
                    pass

            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("No tienes permiso para acceder a este recurso.")

        return wrapper
    return decorator


# ==============================================================================
# EJEMPLO DE USO EN VISTAS
# ==============================================================================

"""
# views.py de billing

@treasurer_required
def approve_payment(request, payment_id):
    # Solo tesorero puede aprobar
    payment = Payment.objects.get(pk=payment_id)
    payment.approve(user=request.user)
    return redirect('billing:payments')


@own_resource_or_permission('billing.view')
def view_invoice(request, invoice_id):
    # Miembros ven sus facturas, tesorero ve todas
    invoice = Invoice.objects.get(pk=invoice_id)
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


# views.py de governance

@board_member_required
def create_meeting(request):
    # Solo junta directiva
    if request.method == 'POST':
        form = MeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = request.user
            meeting.save()
    return render(request, 'governance/meeting_form.html')


class MemberListView(ACLPermissionMixin, ListView):
    model = Member
    module_code = 'members'
    required_action = 'view'

    def get_queryset(self):
        qs = super().get_queryset()

        # Si es miembro regular, ocultar datos sensibles
        if self.request.user.has_role('member'):
            # Usar select_related pero sin campos sensibles
            qs = qs.defer('phone', 'email', 'address', 'dni')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Determinar qué campos mostrar según rol
        context['show_sensitive_data'] = (
            self.request.user.has_role('treasurer') or
            self.request.user.has_role('board_member')
        )

        return context
"""


# ==============================================================================
# CONFIGURACIÓN DE PERMISOS DESDE ADMIN
# ==============================================================================

def ejemplo_configuracion_admin():
    """
    Cómo configurar estos permisos desde el admin de Django
    """
    print("""
    ============================================
    CONFIGURACIÓN DESDE DJANGO ADMIN
    ============================================

    1. CREAR ROL TESORERO:
    ----------------------
    Role:
      - Name: "Tesorero"
      - Code: "treasurer"
      - Level: "treasurer"
      - Description: "Encargado de las finanzas de la asociación"

    2. CONFIGURAR ACCESO A MÓDULOS:
    --------------------------------
    RoleModuleAccess para Tesorero:

      Módulo: Billing
      - Acciones: [view, add, change, delete, manage_payments, export, approve]

      Módulo: Members
      - Acciones: [view, export, view_sensitive]

      Módulo: Panel
      - Acciones: [view, view_reports, generate_report]

    3. CREAR ROL MIEMBRO:
    ---------------------
    Role:
      - Name: "Miembro"
      - Code: "member"
      - Level: "member"
      - Description: "Miembro regular de la asociación"

    4. CONFIGURAR ACCESO LIMITADO:
    -------------------------------
    RoleModuleAccess para Miembro:

      Módulo: Members
      - Acciones: [view]  # Solo directorio básico

      Módulo: Billing
      - Acciones: [view]  # Solo sus facturas (filtrado en vista)

      Módulo: Documents
      - Acciones: [view]  # Solo documentos públicos

    ============================================
    RESULTADO:
    ============================================

    Tesorero (María García):
      ✅ Ve todas las facturas y pagos
      ✅ Puede aprobar pagos
      ✅ Genera reportes financieros
      ✅ Ve datos sensibles de miembros
      ✅ Exporta información financiera
      ❌ NO puede crear reuniones de junta

    Miembro (Juan Pérez):
      ✅ Ve el directorio de miembros (sin datos sensibles)
      ✅ Ve sus propias facturas
      ✅ Accede a documentos públicos
      ✅ Ve noticias y eventos
      ❌ NO puede ver facturas de otros
      ❌ NO puede aprobar pagos
      ❌ NO puede gestionar miembros

    Junta Directiva (Ana López):
      ✅ Gestiona miembros completamente
      ✅ Crea y gestiona reuniones
      ✅ Aprueba decisiones
      ✅ Envía comunicaciones
      ✅ Define estrategia
      ✅ Ve reportes completos
    """)


if __name__ == "__main__":
    # Mostrar ejemplos
    examples = GranularPermissionsExample()

    print("=" * 80)
    print("PERMISOS GRANULARES PyMEMAD: SISTEMA ACL")
    print("=" * 80)

    print("\n📋 CONFIGURACIÓN TESORERO:")
    print("-" * 40)
    treasurer_config = examples.configuracion_tesorero()
    print(f"Rol: {treasurer_config['rol']}")
    print(f"Nivel: {treasurer_config['nivel']}")
    print("\nMódulos y acciones:")
    for module, config in treasurer_config['RoleModuleAccess']['modules'].items():
        print(f"\n  {module.upper()}:")
        for action in config['enabled_actions']:
            print(f"    ✅ {action}")

    print("\n📋 CONFIGURACIÓN MIEMBRO:")
    print("-" * 40)
    member_config = examples.configuracion_miembro()
    print(f"Rol: {member_config['rol']}")
    print(f"Nivel: {member_config['nivel']}")
    print("\nMódulos y acciones:")
    for module, config in member_config['RoleModuleAccess']['modules'].items():
        print(f"\n  {module.upper()}:")
        for action in config['enabled_actions']:
            print(f"    ✅ {action}")

    print("\n" + "=" * 80)
    print("TABLA COMPARATIVA DE PERMISOS")
    print("=" * 80)

    comparison = examples.comparacion_permisos()

    # Imprimir tabla
    print(f"\n{'Permiso':<30} {'Miembro':<15} {'Tesorero':<15} {'Junta':<15}")
    print("-" * 75)
    for row in comparison['rows']:
        print(f"{row[0]:<30} {row[1]:<15} {row[2]:<15} {row[3]:<15}")

    # Mostrar configuración desde admin
    print("\n" + "=" * 80)
    ejemplo_configuracion_admin()