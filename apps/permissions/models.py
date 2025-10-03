# apps/permissions/models.py
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class Module(models.Model):
    """
    Define los módulos/apps del sistema con sus permisos y estructura jerárquica
    """
    # Tipos de acciones disponibles en el sistema
    ACTION_CHOICES = [
        # CRUD Básico
        ('view', 'Ver'),
        ('add', 'Crear'),
        ('change', 'Modificar'),
        ('delete', 'Eliminar'),

        # Gestión
        ('approve', 'Aprobar'),
        ('reject', 'Rechazar'),
        ('assign', 'Asignar'),
        ('transfer', 'Transferir'),

        # Datos
        ('export', 'Exportar'),
        ('import', 'Importar'),
        ('backup', 'Respaldar'),

        # Operaciones especiales
        ('generate_report', 'Generar Reporte'),
        ('manage_payments', 'Gestionar Pagos'),
        ('view_sensitive', 'Ver Datos Sensibles'),
        ('bulk_update', 'Actualización Masiva'),

        # Control y auditoría
        ('audit', 'Auditar'),
        ('override', 'Anular Reglas'),
        ('restore', 'Restaurar'),
    ]

    # Módulo padre (null para módulos de nivel superior)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='submodules',
        verbose_name='Módulo Padre',
        help_text='Módulo padre para crear jerarquía'
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    app_label = models.CharField(
        max_length=50,
        verbose_name='App Django',
        help_text='Nombre de la app Django (ej: members, billing, governance)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Icono',
        help_text='Clase CSS del icono'
    )
    url_namespace = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Namespace URL'
    )

    # Acciones disponibles para este módulo
    available_actions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Acciones Disponibles',
        help_text='Lista de acciones disponibles para este módulo'
    )

    order = models.IntegerField(
        default=0,
        verbose_name='Orden de visualización'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
        ordering = ['order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_top_level(self):
        """Verifica si es un módulo de nivel superior"""
        return self.parent is None

    @property
    def level(self):
        """Retorna el nivel del módulo en la jerarquía"""
        return 'top' if self.is_top_level else 'sub'

    def get_all_submodules(self):
        """Obtiene todos los submódulos recursivamente"""
        submodules = list(self.submodules.all())
        for sub in self.submodules.all():
            submodules.extend(sub.get_all_submodules())
        return submodules

    def get_hierarchy_path(self):
        """Obtiene la ruta completa en la jerarquía"""
        if self.parent:
            parent_path = self.parent.get_hierarchy_path()
            return f"{parent_path} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        """Override save to set default actions if empty"""
        if not self.available_actions:
            # Por defecto, todos los módulos tienen CRUD básico
            self.available_actions = ['view', 'add', 'change', 'delete']
        super().save(*args, **kwargs)

    def get_available_actions(self):
        """Obtiene las acciones disponibles para este módulo"""
        if not self.available_actions:
            return ['view', 'add', 'change', 'delete']
        return self.available_actions

    def get_action_display(self, action_code):
        """Obtiene el nombre para mostrar de una acción"""
        for code, display in self.ACTION_CHOICES:
            if code == action_code:
                return display
        return action_code

    def has_action(self, action_code):
        """Verifica si el módulo tiene una acción específica disponible"""
        return action_code in self.get_available_actions()


class ModulePermission(models.Model):
    """
    Define permisos específicos por módulo
    """
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='module_permissions',
        verbose_name='Módulo'
    )
    code = models.CharField(
        max_length=100,
        verbose_name='Código'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )

    # Tipo de permiso
    PERMISSION_TYPE = (
        ('view', 'Ver'),
        ('add', 'Crear'),
        ('change', 'Modificar'),
        ('delete', 'Eliminar'),
        ('approve', 'Aprobar'),
        ('export', 'Exportar'),
        ('import', 'Importar'),
        ('special', 'Especial'),
    )
    permission_type = models.CharField(
        max_length=20,
        choices=PERMISSION_TYPE,
        verbose_name='Tipo'
    )

    # Relación con permisos Django nativos
    django_permission = models.ForeignKey(
        Permission,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Permiso Django'
    )

    class Meta:
        verbose_name = "Permiso de Módulo"
        verbose_name_plural = "Permisos de Módulos"
        unique_together = [['module', 'code']]
        ordering = ['module', 'permission_type', 'name']

    def __str__(self):
        return f"{self.module.name} - {self.name}"


class Role(models.Model):
    """
    Roles del sistema con permisos modulares y alcance (scope)
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )

    # Nivel del rol - Actualizado con más perfiles específicos
    LEVEL_CHOICES = (
        # Administración del sistema
        ('super_admin', 'Super Administrador'),
        ('admin', 'Administrador'),

        # Gobernanza Nacional
        ('national_president', 'Presidente Nacional'),
        ('national_vice_president', 'Vicepresidente Nacional'),
        ('national_treasurer', 'Tesorero Nacional'),
        ('national_secretary', 'Secretario Nacional'),
        ('national_director', 'Director Nacional'),
        ('national_board_member', 'Miembro Junta Nacional'),

        # Gobernanza Regional
        ('regional_president', 'Presidente Regional'),
        ('regional_vice_president', 'Vicepresidente Regional'),
        ('regional_treasurer', 'Tesorero Regional'),
        ('regional_secretary', 'Secretario Regional'),
        ('regional_director', 'Director Regional'),
        ('regional_board_member', 'Miembro Junta Regional'),

        # Roles operativos
        ('administrative', 'Administrativo'),
        ('accountant', 'Contador'),
        ('auditor', 'Auditor'),

        # Miembros
        ('active_member', 'Socio Activo'),
        ('honorary_member', 'Socio Honorario'),
        ('founder_member', 'Socio Fundador'),
        ('member', 'Miembro Regular'),
        ('external', 'Externo'),
    )
    level = models.CharField(
        max_length=30,
        choices=LEVEL_CHOICES,
        verbose_name='Nivel'
    )

    # Gobernanza del rol
    GOVERNANCE_CHOICES = (
        ('national', 'Nacional - Acceso a todas las regiones'),
        ('regional', 'Regional - Acceso a regiones específicas'),
    )
    governance = models.CharField(
        max_length=20,
        choices=GOVERNANCE_CHOICES,
        default='regional',
        verbose_name='Gobernanza',
        help_text='Define el límite territorial máximo del rol'
    )

    # Regiones permitidas (solo para gobernanza regional)
    allowed_regions = models.ManyToManyField(
        'core.PymeMadRegion',
        blank=True,
        verbose_name='Regiones Permitidas',
        help_text='Regiones a las que tiene acceso (solo para gobernanza regional)'
    )

    # Grupo Django para compatibilidad
    django_group = models.OneToOneField(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Grupo Django'
    )

    # Configuración JSON completa de permisos
    permissions_json = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Configuración de permisos',
        help_text='Configuración completa de permisos del rol en formato JSON'
    )

    # Configuración
    is_system = models.BooleanField(
        default=False,
        verbose_name='Rol del sistema',
        help_text='Los roles del sistema no pueden ser eliminados'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )

    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['level', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Crear o actualizar grupo Django
        if not self.django_group:
            group_name = f"role_{self.code}"
            # Intentar obtener grupo existente o crear uno nuevo
            try:
                self.django_group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                self.django_group = Group.objects.create(name=group_name)

        super().save(*args, **kwargs)

    def sync_users_from_django_group(self):
        """Sincroniza usuarios del grupo Django al sistema de roles"""
        if self.django_group:
            from apps.accounts.models import User
            for user in self.django_group.user_set.all():
                if not hasattr(user, 'primary_role') or not user.primary_role:
                    user.primary_role = self
                    user.save()
                elif self not in user.additional_roles.all():
                    user.additional_roles.add(self)

    def get_module_permissions(self, module_code):
        """Obtiene los permisos para un módulo específico"""
        if not self.permissions_json:
            return {}

        permissions_config = self.permissions_json.get('permissions_config', {})
        return permissions_config.get(module_code, {})

    def get_modules(self):
        """Obtiene los módulos asociados a este rol"""
        from apps.permissions.models import RoleModuleAccess

        module_accesses = RoleModuleAccess.objects.filter(role=self).select_related('module')
        return [access.module for access in module_accesses]

    @property
    def modules(self):
        """Propiedad para acceder a los módulos del rol"""
        return self.get_modules()

    @property
    def primary_users(self):
        """Obtiene los usuarios que tienen este rol como principal"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(primary_role=self)

    @property
    def additional_users(self):
        """Obtiene los usuarios que tienen este rol como adicional"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(additional_roles=self)

    def get_all_users(self):
        """Obtiene todos los usuarios asociados a este rol (principal + adicional)"""
        from django.contrib.auth import get_user_model
        from django.db.models import Q
        User = get_user_model()
        return User.objects.filter(
            Q(primary_role=self) | Q(additional_roles=self)
        ).distinct()

    # ========== MÉTODOS SIMPLIFICADOS PARA PERMISOS ==========

    def has_module_action(self, module_code, action_code):
        """
        Verifica si el rol tiene una acción específica en un módulo
        Ejemplo: role.has_module_action('members', 'manage_payments')
        """
        try:
            # Verificar en RoleModuleAccess
            access = RoleModuleAccess.objects.get(role=self, module__code=module_code)
            return access.has_action(action_code)
        except RoleModuleAccess.DoesNotExist:
            return False

    def grant_module_action(self, module_code, action_code):
        """
        Otorga una acción específica en un módulo al rol
        """
        try:
            module = Module.objects.get(code=module_code)
            access, created = RoleModuleAccess.objects.get_or_create(
                role=self,
                module=module
            )
            return access.enable_action(action_code)
        except Module.DoesNotExist:
            return False

    def revoke_module_action(self, module_code, action_code):
        """
        Revoca una acción específica en un módulo al rol
        """
        try:
            access = RoleModuleAccess.objects.get(role=self, module__code=module_code)
            return access.disable_action(action_code)
        except RoleModuleAccess.DoesNotExist:
            return False

    def get_all_permissions(self):
        """
        Obtiene todos los permisos del rol organizados por módulo
        """
        permissions = {}
        for access in RoleModuleAccess.objects.filter(role=self).select_related('module'):
            permissions[access.module.code] = access.enabled_actions
        return permissions

    def is_national_level(self):
        """Verifica si es un rol de nivel nacional"""
        national_levels = [
            'super_admin', 'admin', 'national_president',
            'national_vice_president', 'national_treasurer',
            'national_secretary', 'national_director', 'national_board_member'
        ]
        return self.level in national_levels or self.scope == 'national'

    def is_regional_level(self):
        """Verifica si es un rol de nivel regional"""
        regional_levels = [
            'regional_president', 'regional_vice_president',
            'regional_treasurer', 'regional_secretary',
            'regional_director', 'regional_board_member'
        ]
        return self.level in regional_levels or self.scope == 'regional'

    def can_manage_region(self, region_code=None):
        """
        Verifica si el rol puede gestionar una región específica
        """
        # Roles nacionales pueden gestionar cualquier región
        if self.is_national_level():
            return True

        # Roles con scope 'all' pueden gestionar cualquier región
        if self.scope == 'all':
            return True

        # Para roles regionales, necesitamos verificar la región específica
        # Esto se verificaría en conjunto con UserRegionalScope
        return self.is_regional_level() and region_code is not None

    def get_hierarchy_level(self):
        """
        Retorna el nivel jerárquico del rol (para comparación)
        Menor número = mayor jerarquía
        """
        hierarchy = {
            # Sistema
            'super_admin': 0,
            'admin': 1,

            # Nacional
            'national_president': 10,
            'national_vice_president': 11,
            'national_treasurer': 12,
            'national_secretary': 12,
            'national_director': 13,
            'national_board_member': 14,

            # Regional
            'regional_president': 20,
            'regional_vice_president': 21,
            'regional_treasurer': 22,
            'regional_secretary': 22,
            'regional_director': 23,
            'regional_board_member': 24,

            # Operativo
            'administrative': 30,
            'accountant': 31,
            'auditor': 32,

            # Miembros
            'founder_member': 40,
            'honorary_member': 41,
            'active_member': 42,
            'member': 43,
            'external': 99,
        }
        return hierarchy.get(self.level, 100)


class RoleModuleAccess(models.Model):
    """
    Define el acceso de un rol a un módulo específico
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        verbose_name='Rol'
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        verbose_name='Módulo'
    )

    # Permisos en el módulo
    permissions = models.ManyToManyField(
        ModulePermission,
        related_name='role_accesses',
        verbose_name='Permisos',
        blank=True
    )

    # Permisos específicos del módulo (se almacenan las acciones habilitadas)
    enabled_actions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Acciones Habilitadas',
        help_text='Lista de códigos de acciones habilitadas para este rol en este módulo'
    )

    # Alcance específico para este módulo
    MODULE_SCOPE_CHOICES = (
        ('all', 'Todos - Ve todos los datos dentro de su gobernanza'),
        ('own', 'Propio - Solo sus propios datos'),
    )
    scope = models.CharField(
        max_length=20,
        choices=MODULE_SCOPE_CHOICES,
        default='own',
        verbose_name='Alcance del Módulo',
        help_text='Define qué datos puede ver dentro de su gobernanza'
    )

    # Configuración adicional
    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Configuración',
        help_text='Configuración específica del módulo para este rol'
    )

    class Meta:
        verbose_name = "Acceso de Rol a Módulo"
        verbose_name_plural = "Accesos de Roles a Módulos"
        unique_together = [['role', 'module']]

    def __str__(self):
        return f"{self.role.name} -> {self.module.name}"

    def has_action(self, action_code):
        """Verifica si el rol tiene una acción específica habilitada en este módulo"""
        return action_code in self.enabled_actions

    def enable_action(self, action_code):
        """Habilita una acción específica para este rol en este módulo"""
        if self.module.has_action(action_code):
            if action_code not in self.enabled_actions:
                self.enabled_actions.append(action_code)
                self.save()
                return True
        return False

    def disable_action(self, action_code):
        """Deshabilita una acción específica para este rol en este módulo"""
        if action_code in self.enabled_actions:
            self.enabled_actions.remove(action_code)
            self.save()
            return True
        return False

    def get_enabled_actions_display(self):
        """Obtiene los nombres para mostrar de las acciones habilitadas"""
        return [self.module.get_action_display(action) for action in self.enabled_actions]

    def sync_with_module_actions(self):
        """Sincroniza las acciones habilitadas con las disponibles en el módulo"""
        module_actions = self.module.get_available_actions()
        # Remover acciones que ya no están disponibles en el módulo
        self.enabled_actions = [a for a in self.enabled_actions if a in module_actions]
        self.save()


class UserRegionalScope(models.Model):
    """
    Define el alcance regional de un usuario para sus permisos
    """
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='regional_scopes',
        verbose_name='Usuario'
    )

    # Región a la que tiene acceso
    region = models.ForeignKey(
        'core.PymeMadRegion',
        on_delete=models.CASCADE,
        related_name='user_scopes',
        verbose_name='Región',
        null=True,
        blank=True
    )

    # Nivel de acceso en esta región
    ACCESS_LEVEL_CHOICES = (
        ('full', 'Acceso Completo'),
        ('read', 'Solo Lectura'),
        ('limited', 'Limitado'),
    )
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='full',
        verbose_name='Nivel de Acceso'
    )

    # Si es su región principal
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Región Principal'
    )

    # Activo
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )

    # Fechas
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='region_assignments_made',
        verbose_name='Asignado por'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de expiración',
        help_text='Dejar en blanco para acceso permanente'
    )

    class Meta:
        verbose_name = "Alcance Regional de Usuario"
        verbose_name_plural = "Alcances Regionales de Usuarios"
        unique_together = [['user', 'region']]
        ordering = ['user', '-is_primary', 'region']

    def __str__(self):
        if self.region:
            return f"{self.user} - {self.region.name} ({self.get_access_level_display()})"
        return f"{self.user} - Nacional ({self.get_access_level_display()})"

    def is_valid(self):
        """Verifica si el alcance sigue siendo válido"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def save(self, *args, **kwargs):
        # Si es la región principal, desmarcar otras
        if self.is_primary:
            UserRegionalScope.objects.filter(
                user=self.user
            ).exclude(id=self.id if self.id else None).update(is_primary=False)
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """
    Registro de auditoría para cambios en permisos
    """
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='permission_audit_logs',
        verbose_name='Usuario afectado'
    )

    # Tipo de acción
    ACTION_CHOICES = (
        ('role_assigned', 'Rol asignado'),
        ('role_removed', 'Rol removido'),
        ('permission_added', 'Permiso agregado'),
        ('permission_removed', 'Permiso removido'),
        ('module_access_granted', 'Acceso a módulo otorgado'),
        ('module_access_revoked', 'Acceso a módulo revocado'),
        ('region_access_granted', 'Acceso regional otorgado'),
        ('region_access_revoked', 'Acceso regional revocado'),
        ('scope_changed', 'Alcance modificado'),
        ('user_activated', 'Usuario activado'),
        ('user_deactivated', 'Usuario desactivado'),
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name='Acción'
    )

    # Información de scope/región si aplica
    affected_region = models.ForeignKey(
        'core.PymeMadRegion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Región afectada'
    )

    # Detalles
    details = models.JSONField(
        default=dict,
        verbose_name='Detalles'
    )

    # IP y navegador
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Dirección IP'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )

    # Quién realizó la acción
    performed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='permission_actions_performed',
        verbose_name='Realizado por'
    )

    # Cuándo
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['user', '-performed_at']),
            models.Index(fields=['action', '-performed_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.user} - {self.performed_at}"
