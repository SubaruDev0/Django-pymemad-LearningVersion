from django.core.management.base import BaseCommand
from apps.permissions.models import Module


class Command(BaseCommand):
    help = 'Carga los módulos iniciales del sistema PyMEMAD basados en la estructura actual'

    def get_default_actions_for_module(self, module_code):
        """Determina las acciones predeterminadas basadas en el tipo de módulo"""
        # Acciones básicas CRUD
        crud_basic = ['view', 'add', 'change', 'delete']
        crud_readonly = ['view']
        crud_modify = ['view', 'change']

        # Módulos de solo lectura
        if module_code == 'dashboard':
            return crud_readonly

        if module_code.startswith('reports'):
            if 'financial' in module_code:
                return ['view', 'export', 'generate_report']
            return ['view', 'export']

        # Módulos de configuración
        if module_code.startswith('settings'):
            if module_code == 'settings_backup':
                return ['view', 'add', 'export', 'backup']
            elif module_code == 'settings_regions':
                return crud_basic
            elif module_code == 'settings':
                return crud_modify
            else:
                return crud_modify

        # Módulos de auditoría
        if 'audit' in module_code:
            return ['view', 'export', 'audit']

        # Módulos de comunicaciones
        if module_code.startswith('communications'):
            # Todos los módulos de comunicaciones tienen CRUD completo
            # Las acciones especiales como 'send' o 'publish' no existen en ACTION_CHOICES
            return crud_basic

        # Módulos de gobernanza
        if module_code.startswith('governance'):
            if module_code == 'governance':
                return crud_basic + ['approve', 'export']
            elif 'voting' in module_code:
                return crud_basic + ['approve', 'export']
            elif 'board' in module_code:
                return ['view', 'add', 'change', 'approve']
            elif 'minutes' in module_code or 'meetings' in module_code:
                return crud_basic + ['approve']
            elif 'committees' in module_code:
                return crud_basic + ['assign']
            else:
                return crud_basic + ['approve']

        # Módulos de facturación
        if module_code.startswith('billing'):
            if module_code == 'billing':
                return crud_basic + ['export', 'manage_payments']
            elif 'payments' in module_code:
                # Pagos no se eliminan, solo se registran y modifican
                return ['view', 'add', 'change', 'export']
            elif 'invoices' in module_code:
                return crud_basic + ['export']
            elif 'reports' in module_code:
                return ['view', 'export', 'generate_report']
            elif 'expenses' in module_code:
                return crud_basic + ['export', 'approve']
            elif 'fees' in module_code:
                return crud_basic
            else:
                return crud_basic + ['export']

        # Módulos de miembros
        if module_code.startswith('members'):
            if module_code == 'members':  # Módulo principal
                return crud_basic + ['export', 'import', 'approve', 'reject', 'bulk_update']
            elif 'companies' in module_code:
                return crud_basic + ['export', 'approve']
            elif 'memberships' in module_code:
                return crud_basic + ['approve']
            else:
                return crud_basic + ['export']

        # Módulos de eventos
        if module_code.startswith('events'):
            if module_code == 'events':  # Módulo principal
                return crud_basic
            elif 'registration' in module_code:
                return crud_basic + ['approve']
            elif 'notifications' in module_code:
                # Notificaciones solo se crean y ven
                return ['view', 'add']
            else:
                return crud_basic

        # Módulos de noticias
        if module_code.startswith('news'):
            if module_code == 'news':  # Módulo principal
                return crud_basic
            elif 'comments' in module_code:
                # Comentarios: ver, aprobar y eliminar
                return ['view', 'approve', 'delete']
            else:
                return crud_basic

        # Módulos de documentos
        if module_code.startswith('documents'):
            if module_code == 'documents':  # Módulo principal
                return crud_basic + ['export']
            elif 'legal' in module_code:
                # Documentos legales no se eliminan
                return ['view', 'add', 'change', 'approve']
            else:
                return crud_basic

        # Módulos de estrategia
        if module_code.startswith('strategy'):
            if module_code == 'strategy':  # Módulo principal
                return crud_basic + ['approve']
            elif 'planning' in module_code:
                return ['view', 'add', 'change', 'approve']
            elif 'projects' in module_code:
                return crud_basic + ['assign']
            else:
                return crud_basic

        # Módulos de permisos
        if module_code.startswith('permissions'):
            if module_code == 'permissions':  # Módulo principal
                return crud_basic + ['assign']
            elif 'users' in module_code:
                return crud_basic + ['assign']
            elif 'audit' in module_code:
                return ['view', 'export', 'audit']
            else:
                return crud_basic

        # Por defecto: CRUD completo
        return crud_basic

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Cargando módulos del sistema PyMEMAD...'))

        # Definir la estructura de módulos basada en la arquitectura de PyMEMAD
        modules_data = [
            # ========== MÓDULOS PRINCIPALES ==========

            # Dashboard y Panel Principal
            {
                'code': 'dashboard',
                'name': 'Panel Principal',
                'app_label': 'panel',
                'description': 'Panel de control y estadísticas generales del sistema',
                'icon': 'ai-home',
                'url_namespace': 'dashboard',
                'available_actions': self.get_default_actions_for_module('dashboard'),
                'order': 10,
                'parent': None,
            },

            # Gestión de Miembros
            {
                'code': 'members',
                'name': 'Gestión de Miembros',
                'app_label': 'members',
                'description': 'Administración completa de socios y empresas asociadas',
                'icon': 'ai-user-group',
                'url_namespace': 'members',
                'available_actions': self.get_default_actions_for_module('members'),
                'order': 20,
                'parent': None,
            },
            {
                'code': 'members_persons',
                'name': 'Personas',
                'app_label': 'members',
                'description': 'Gestión de personas asociadas',
                'url_namespace': 'members',
                'available_actions': self.get_default_actions_for_module('members_persons'),
                'order': 1,
                'parent': 'members',
            },
            {
                'code': 'members_companies',
                'name': 'Empresas',
                'app_label': 'members',
                'description': 'Gestión de empresas miembro',
                'url_namespace': 'members',
                'available_actions': self.get_default_actions_for_module('members_companies'),
                'order': 2,
                'parent': 'members',
            },
            {
                'code': 'members_memberships',
                'name': 'Membresías',
                'app_label': 'members',
                'description': 'Control de membresías activas',
                'url_namespace': 'members',
                'available_actions': self.get_default_actions_for_module('members_memberships'),
                'order': 3,
                'parent': 'members',
            },
            {
                'code': 'members_categories',
                'name': 'Categorías',
                'app_label': 'members',
                'description': 'Categorías de miembros',
                'url_namespace': 'members',
                'available_actions': self.get_default_actions_for_module('members_categories'),
                'order': 4,
                'parent': 'members',
            },

            # Facturación y Finanzas
            {
                'code': 'billing',
                'name': 'Facturación',
                'app_label': 'billing',
                'description': 'Sistema de facturación y gestión financiera',
                'icon': 'ai-file-text',
                'url_namespace': 'billing',
                'available_actions': self.get_default_actions_for_module('billing'),
                'order': 30,
                'parent': None,
            },
            {
                'code': 'billing_invoices',
                'name': 'Facturas',
                'app_label': 'billing',
                'description': 'Gestión de facturas emitidas',
                'url_namespace': 'billing',
                'available_actions': self.get_default_actions_for_module('billing_invoices'),
                'order': 1,
                'parent': 'billing',
            },
            {
                'code': 'billing_payments',
                'name': 'Pagos',
                'app_label': 'billing',
                'description': 'Registro y control de pagos',
                'url_namespace': 'billing',
                'available_actions': self.get_default_actions_for_module('billing_payments'),
                'order': 2,
                'parent': 'billing',
            },
            {
                'code': 'billing_fees',
                'name': 'Cuotas',
                'app_label': 'billing',
                'description': 'Gestión de cuotas y periodicidad',
                'url_namespace': 'billing',
                'available_actions': self.get_default_actions_for_module('billing_fees'),
                'order': 3,
                'parent': 'billing',
            },
            {
                'code': 'billing_expenses',
                'name': 'Gastos y Egresos',
                'app_label': 'billing',
                'description': 'Control de gastos y egresos',
                'url_namespace': 'billing',
                'available_actions': self.get_default_actions_for_module('billing_expenses'),
                'order': 4,
                'parent': 'billing',
            },
            {
                'code': 'billing_reports',
                'name': 'Reportes Financieros',
                'app_label': 'billing',
                'description': 'Balance y estados de resultados',
                'url_namespace': 'billing',
                'available_actions': self.get_default_actions_for_module('billing_reports'),
                'order': 5,
                'parent': 'billing',
            },

            # Gobernanza
            {
                'code': 'governance',
                'name': 'Gobernanza',
                'app_label': 'governance',
                'description': 'Gestión de la estructura de gobierno asociativo',
                'icon': 'ai-award',
                'url_namespace': 'governance',
                'available_actions': self.get_default_actions_for_module('governance'),
                'order': 40,
                'parent': None,
            },
            {
                'code': 'governance_meetings',
                'name': 'Asambleas y Reuniones',
                'app_label': 'governance',
                'description': 'Gestión de asambleas y reuniones oficiales',
                'url_namespace': 'governance',
                'available_actions': self.get_default_actions_for_module('governance_meetings'),
                'order': 1,
                'parent': 'governance',
            },
            {
                'code': 'governance_board',
                'name': 'Directorio',
                'app_label': 'governance',
                'description': 'Gestión del directorio y cargos',
                'url_namespace': 'governance',
                'available_actions': self.get_default_actions_for_module('governance_board'),
                'order': 2,
                'parent': 'governance',
            },
            {
                'code': 'governance_minutes',
                'name': 'Actas',
                'app_label': 'governance',
                'description': 'Registro y gestión de actas oficiales',
                'url_namespace': 'governance',
                'available_actions': self.get_default_actions_for_module('governance_minutes'),
                'order': 3,
                'parent': 'governance',
            },
            {
                'code': 'governance_voting',
                'name': 'Votaciones',
                'app_label': 'governance',
                'description': 'Sistema de votaciones electrónicas',
                'url_namespace': 'governance',
                'available_actions': self.get_default_actions_for_module('governance_voting'),
                'order': 4,
                'parent': 'governance',
            },
            {
                'code': 'governance_committees',
                'name': 'Comités',
                'app_label': 'governance',
                'description': 'Gestión de comités y grupos de trabajo',
                'url_namespace': 'governance',
                'available_actions': self.get_default_actions_for_module('governance_committees'),
                'order': 5,
                'parent': 'governance',
            },

            # Comunicaciones
            {
                'code': 'communications',
                'name': 'Comunicaciones',
                'app_label': 'communications',
                'description': 'Sistema de comunicación y mensajería',
                'icon': 'ai-messages',
                'url_namespace': 'communications',
                'available_actions': self.get_default_actions_for_module('communications'),
                'order': 50,
                'parent': None,
            },
            {
                'code': 'communications_announcements',
                'name': 'Anuncios',
                'app_label': 'communications',
                'description': 'Publicación de anuncios y comunicados',
                'url_namespace': 'communications',
                'available_actions': self.get_default_actions_for_module('communications_announcements'),
                'order': 1,
                'parent': 'communications',
            },
            {
                'code': 'communications_newsletters',
                'name': 'Boletines',
                'app_label': 'communications',
                'description': 'Gestión de boletines informativos',
                'url_namespace': 'communications',
                'available_actions': self.get_default_actions_for_module('communications_newsletters'),
                'order': 2,
                'parent': 'communications',
            },
            {
                'code': 'communications_emails',
                'name': 'Correos Masivos',
                'app_label': 'communications',
                'description': 'Envío de correos masivos',
                'url_namespace': 'communications',
                'available_actions': self.get_default_actions_for_module('communications_emails'),
                'order': 3,
                'parent': 'communications',
            },
            {
                'code': 'communications_templates',
                'name': 'Plantillas',
                'app_label': 'communications',
                'description': 'Plantillas de comunicación',
                'url_namespace': 'communications',
                'available_actions': self.get_default_actions_for_module('communications_templates'),
                'order': 4,
                'parent': 'communications',
            },

            # Documentos
            {
                'code': 'documents',
                'name': 'Documentos',
                'app_label': 'documents',
                'description': 'Gestión documental centralizada',
                'icon': 'ai-folder',
                'url_namespace': 'documents',
                'available_actions': self.get_default_actions_for_module('documents'),
                'order': 60,
                'parent': None,
            },
            {
                'code': 'documents_repository',
                'name': 'Repositorio',
                'app_label': 'documents',
                'description': 'Repositorio central de documentos',
                'url_namespace': 'documents',
                'available_actions': self.get_default_actions_for_module('documents_repository'),
                'order': 1,
                'parent': 'documents',
            },
            {
                'code': 'documents_legal',
                'name': 'Documentos Legales',
                'app_label': 'documents',
                'description': 'Estatutos, reglamentos y documentos legales',
                'url_namespace': 'documents',
                'available_actions': self.get_default_actions_for_module('documents_legal'),
                'order': 2,
                'parent': 'documents',
            },
            {
                'code': 'documents_templates',
                'name': 'Plantillas',
                'app_label': 'documents',
                'description': 'Plantillas de documentos',
                'url_namespace': 'documents',
                'available_actions': self.get_default_actions_for_module('documents_templates'),
                'order': 3,
                'parent': 'documents',
            },

            # Estrategia y Planificación
            {
                'code': 'strategy',
                'name': 'Estrategia',
                'app_label': 'strategy',
                'description': 'Planificación estratégica y objetivos',
                'icon': 'ai-list',
                'url_namespace': 'strategy',
                'available_actions': self.get_default_actions_for_module('strategy'),
                'order': 70,
                'parent': None,
            },
            {
                'code': 'strategy_planning',
                'name': 'Plan Estratégico',
                'app_label': 'strategy',
                'description': 'Definición y seguimiento del plan estratégico',
                'url_namespace': 'strategy',
                'available_actions': self.get_default_actions_for_module('strategy_planning'),
                'order': 1,
                'parent': 'strategy',
            },
            {
                'code': 'strategy_objectives',
                'name': 'Objetivos',
                'app_label': 'strategy',
                'description': 'Gestión de objetivos estratégicos',
                'url_namespace': 'strategy',
                'available_actions': self.get_default_actions_for_module('strategy_objectives'),
                'order': 2,
                'parent': 'strategy',
            },
            {
                'code': 'strategy_kpis',
                'name': 'Indicadores (KPIs)',
                'app_label': 'strategy',
                'description': 'Indicadores clave de desempeño',
                'url_namespace': 'strategy',
                'available_actions': self.get_default_actions_for_module('strategy_kpis'),
                'order': 3,
                'parent': 'strategy',
            },
            {
                'code': 'strategy_projects',
                'name': 'Proyectos',
                'app_label': 'strategy',
                'description': 'Gestión de proyectos estratégicos',
                'url_namespace': 'strategy',
                'available_actions': self.get_default_actions_for_module('strategy_projects'),
                'order': 4,
                'parent': 'strategy',
            },

            # Eventos
            {
                'code': 'events',
                'name': 'Eventos',
                'app_label': 'events',
                'description': 'Gestión de eventos y actividades',
                'icon': 'ai-calendar',
                'url_namespace': 'events',
                'available_actions': self.get_default_actions_for_module('events'),
                'order': 80,
                'parent': None,
            },
            {
                'code': 'events_calendar',
                'name': 'Calendario',
                'app_label': 'events',
                'description': 'Calendario de eventos',
                'url_namespace': 'events',
                'available_actions': self.get_default_actions_for_module('events_calendar'),
                'order': 1,
                'parent': 'events',
            },
            {
                'code': 'events_registration',
                'name': 'Inscripciones',
                'app_label': 'events',
                'description': 'Gestión de inscripciones a eventos',
                'url_namespace': 'events',
                'available_actions': self.get_default_actions_for_module('events_registration'),
                'order': 2,
                'parent': 'events',
            },
            {
                'code': 'events_notifications',
                'name': 'Notificaciones',
                'app_label': 'events',
                'description': 'Notificaciones de eventos',
                'url_namespace': 'events',
                'available_actions': self.get_default_actions_for_module('events_notifications'),
                'order': 3,
                'parent': 'events',
            },

            # Noticias y Blog
            {
                'code': 'news',
                'name': 'Noticias',
                'app_label': 'news',
                'description': 'Gestión de noticias y blog',
                'icon': 'ai-file-text',
                'url_namespace': 'news',
                'available_actions': self.get_default_actions_for_module('news'),
                'order': 90,
                'parent': None,
            },
            {
                'code': 'news_posts',
                'name': 'Publicaciones',
                'app_label': 'news',
                'description': 'Gestión de publicaciones',
                'url_namespace': 'news',
                'available_actions': self.get_default_actions_for_module('news_posts'),
                'order': 1,
                'parent': 'news',
            },
            {
                'code': 'news_categories',
                'name': 'Categorías',
                'app_label': 'news',
                'description': 'Categorías de noticias',
                'url_namespace': 'news',
                'available_actions': self.get_default_actions_for_module('news_categories'),
                'order': 2,
                'parent': 'news',
            },
            {
                'code': 'news_tags',
                'name': 'Etiquetas',
                'app_label': 'news',
                'description': 'Etiquetas para clasificación',
                'url_namespace': 'news',
                'available_actions': self.get_default_actions_for_module('news_tags'),
                'order': 3,
                'parent': 'news',
            },
            {
                'code': 'news_comments',
                'name': 'Comentarios',
                'app_label': 'news',
                'description': 'Moderación de comentarios',
                'url_namespace': 'news',
                'available_actions': self.get_default_actions_for_module('news_comments'),
                'order': 4,
                'parent': 'news',
            },

            # Configuración del Sistema
            {
                'code': 'settings',
                'name': 'Configuración',
                'app_label': 'core',
                'description': 'Configuración general del sistema',
                'icon': 'ai-settings',
                'url_namespace': 'settings',
                'available_actions': self.get_default_actions_for_module('settings'),
                'order': 100,
                'parent': None,
            },
            {
                'code': 'settings_general',
                'name': 'Configuración General',
                'app_label': 'core',
                'description': 'Parámetros generales del sistema',
                'url_namespace': 'settings',
                'available_actions': self.get_default_actions_for_module('settings_general'),
                'order': 1,
                'parent': 'settings',
            },
            {
                'code': 'settings_regions',
                'name': 'Regiones',
                'app_label': 'core',
                'description': 'Gestión de regiones PyMEMAD',
                'url_namespace': 'settings',
                'available_actions': self.get_default_actions_for_module('settings_regions'),
                'order': 2,
                'parent': 'settings',
            },
            {
                'code': 'settings_email',
                'name': 'Configuración Email',
                'app_label': 'core',
                'description': 'Configuración de correo electrónico',
                'url_namespace': 'settings',
                'available_actions': self.get_default_actions_for_module('settings_email'),
                'order': 3,
                'parent': 'settings',
            },
            {
                'code': 'settings_backup',
                'name': 'Respaldos',
                'app_label': 'core',
                'description': 'Gestión de respaldos del sistema',
                'url_namespace': 'settings',
                'available_actions': self.get_default_actions_for_module('settings_backup'),
                'order': 4,
                'parent': 'settings',
            },

            # Sistema de Permisos
            {
                'code': 'permissions',
                'name': 'Permisos y Roles',
                'app_label': 'permissions',
                'description': 'Gestión de usuarios, roles y permisos del sistema',
                'icon': 'ai-shield',
                'url_namespace': 'permissions',
                'available_actions': self.get_default_actions_for_module('permissions'),
                'order': 110,
                'parent': None,
            },
            {
                'code': 'permissions_users',
                'name': 'Usuarios del Sistema',
                'app_label': 'permissions',
                'description': 'Gestión de usuarios del sistema',
                'url_namespace': 'permissions',
                'available_actions': self.get_default_actions_for_module('permissions_users'),
                'order': 1,
                'parent': 'permissions',
            },
            {
                'code': 'permissions_roles',
                'name': 'Roles',
                'app_label': 'permissions',
                'description': 'Gestión de roles y jerarquías',
                'url_namespace': 'permissions',
                'available_actions': self.get_default_actions_for_module('permissions_roles'),
                'order': 2,
                'parent': 'permissions',
            },
            {
                'code': 'permissions_modules',
                'name': 'Módulos',
                'app_label': 'permissions',
                'description': 'Configuración de módulos y permisos',
                'url_namespace': 'permissions',
                'available_actions': self.get_default_actions_for_module('permissions_modules'),
                'order': 3,
                'parent': 'permissions',
            },
            {
                'code': 'permissions_audit',
                'name': 'Auditoría',
                'app_label': 'permissions',
                'description': 'Registro de auditoría de cambios',
                'url_namespace': 'permissions',
                'available_actions': self.get_default_actions_for_module('permissions_audit'),
                'order': 4,
                'parent': 'permissions',
            },

            # Reportes y Estadísticas
            {
                'code': 'reports',
                'name': 'Reportes',
                'app_label': 'reports',
                'description': 'Reportes y estadísticas del sistema',
                'icon': 'ai-bar-chart-1',
                'url_namespace': 'reports',
                'available_actions': self.get_default_actions_for_module('reports'),
                'order': 120,
                'parent': None,
            },
            {
                'code': 'reports_members',
                'name': 'Reportes de Miembros',
                'app_label': 'reports',
                'description': 'Estadísticas de membresías',
                'url_namespace': 'reports',
                'available_actions': self.get_default_actions_for_module('reports_members'),
                'order': 1,
                'parent': 'reports',
            },
            {
                'code': 'reports_financial',
                'name': 'Reportes Financieros',
                'app_label': 'reports',
                'description': 'Informes financieros y contables',
                'url_namespace': 'reports',
                'available_actions': self.get_default_actions_for_module('reports_financial'),
                'order': 2,
                'parent': 'reports',
            },
            {
                'code': 'reports_activities',
                'name': 'Reportes de Actividades',
                'app_label': 'reports',
                'description': 'Estadísticas de eventos y actividades',
                'url_namespace': 'reports',
                'available_actions': self.get_default_actions_for_module('reports_activities'),
                'order': 3,
                'parent': 'reports',
            },
        ]

        # Crear o actualizar módulos
        created_count = 0
        updated_count = 0

        # Primero crear todos los módulos padre
        self.stdout.write('\n📁 Creando módulos principales...\n')
        for module_data in modules_data:
            if module_data['parent'] is None:
                module, created = Module.objects.update_or_create(
                    code=module_data['code'],
                    defaults={
                        'name': module_data['name'],
                        'app_label': module_data['app_label'],
                        'description': module_data['description'],
                        'icon': module_data.get('icon', ''),
                        'url_namespace': module_data.get('url_namespace', ''),
                        'available_actions': module_data.get('available_actions', ['view', 'add', 'change', 'delete']),
                        'order': module_data['order'],
                        'is_active': True,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  ✅ Creado módulo: {module.name}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  📝 Actualizado módulo: {module.name}")

        # Luego crear los submódulos
        self.stdout.write('\n📂 Creando submódulos...\n')
        for module_data in modules_data:
            if module_data['parent'] is not None:
                try:
                    parent = Module.objects.get(code=module_data['parent'])
                    module, created = Module.objects.update_or_create(
                        code=module_data['code'],
                        defaults={
                            'name': module_data['name'],
                            'app_label': module_data['app_label'],
                            'description': module_data['description'],
                            'icon': module_data.get('icon', ''),
                            'url_namespace': module_data.get('url_namespace', ''),
                            'available_actions': module_data.get('available_actions', ['view', 'add', 'change', 'delete']),
                            'order': module_data['order'],
                            'parent': parent,
                            'is_active': True,
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f"    ➕ Creado: {module.name} (bajo {parent.name})")
                    else:
                        updated_count += 1
                        self.stdout.write(f"    📝 Actualizado: {module.name}")
                except Module.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"    ❌ No se pudo crear {module_data['name']}: módulo padre '{module_data['parent']}' no encontrado")
                    )

        # Resumen final
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado: {created_count} módulos creados, {updated_count} actualizados'
            )
        )

        # Información adicional
        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  NOTA IMPORTANTE:'
                '\n   - Los módulos han sido creados en la base de datos'
                '\n   - Para asignar permisos, use el wizard de configuración de roles'
                '\n   - Los superusuarios tienen acceso automático a todos los módulos'
                '\n   - Use el comando "python manage.py init_acl" para crear roles iniciales'
            )
        )

        # Estadísticas
        total_modules = Module.objects.count()
        parent_modules = Module.objects.filter(parent__isnull=True).count()
        sub_modules = Module.objects.filter(parent__isnull=False).count()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n📊 Estadísticas:'
                f'\n   - Total de módulos: {total_modules}'
                f'\n   - Módulos principales: {parent_modules}'
                f'\n   - Submódulos: {sub_modules}'
            )
        )