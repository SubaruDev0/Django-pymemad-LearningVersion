# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords
from apps.core.mixins import TimestampedModel

def upload_to_avatars(instance, filename):
    """Genera una ruta única para el avatar basada en el ID del usuario."""
    return f'avatars/user_{instance.id}_{filename.split(".")[-1].lower()}'

class User(AbstractUser, TimestampedModel):
    """
    Usuario del sistema - Solo datos personales
    La información empresarial está en Member
    La relación con regiones está en PymeMadMembership
    """
    # === Campos para el perfil ===
    avatar = models.ImageField(
        upload_to=upload_to_avatars,
        null=True,
        blank=True,
        help_text="Foto de perfil del usuario"
    )
    bio = models.TextField(
        blank=True,
        help_text="Biografía o descripción personal"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Número de teléfono de contacto"
    )

    # === Roles ACL ===
    primary_role = models.ForeignKey(
        'permissions.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_users',
        verbose_name='Rol Principal'
    )
    additional_roles = models.ManyToManyField(
        'permissions.Role',
        blank=True,
        related_name='additional_users',
        verbose_name='Roles Adicionales'
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['-created_at']

    def __str__(self):
        return self.get_full_name() or self.username

    def get_display_name(self):
        """Nombre para mostrar en la interfaz"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    # Métodos auxiliares
    def get_active_memberships(self):
        """Obtiene todas las membresías activas del usuario"""
        if hasattr(self, 'person_profile') and self.person_profile:
            # Obtener empresas donde la persona es contacto
            from apps.members.models import Membership
            companies = self.person_profile.company_contacts.values_list('company', flat=True)
            return Membership.objects.filter(
                company__in=companies,
                status='active'
            )
        from apps.members.models import Membership
        return Membership.objects.none()

    def get_companies(self):
        """Obtiene todas las empresas donde el usuario está activo"""
        if hasattr(self, 'person_profile') and self.person_profile:
            from apps.members.models import Company
            return Company.objects.filter(
                contacts__person=self.person_profile
            ).distinct()
        from apps.members.models import Company
        return Company.objects.none()
    def get_regions(self):
        """Obtiene todas las regiones donde el usuario tiene membresías activas"""
        if hasattr(self, 'person_profile') and self.person_profile:
            from apps.core.models import PymeMadRegion
            active_memberships = self.get_active_memberships()
            region_ids = active_memberships.values_list('region', flat=True)
            return PymeMadRegion.objects.filter(id__in=region_ids).distinct()
        from apps.core.models import PymeMadRegion
        return PymeMadRegion.objects.none()

    def has_national_access(self):
        """Verifica si tiene acceso a nivel nacional"""
        if self.is_superuser:
            return True
        
        if hasattr(self, 'person_profile') and self.person_profile:
            from apps.core.models import BoardPosition
            # Verificar si tiene un cargo nacional activo
            return BoardPosition.objects.filter(
                person=self.person_profile,
                level='national',
                is_active=True
            ).exists()
        return False

    def has_regional_access(self, region):
        """Verifica si tiene acceso a una región específica"""
        if self.has_national_access():
            return True
            
        if hasattr(self, 'person_profile') and self.person_profile:
            from apps.core.models import BoardPosition
            # Verificar si tiene un cargo regional activo en esa región
            regional_access = BoardPosition.objects.filter(
                person=self.person_profile,
                level='regional',
                region=region,
                is_active=True
            ).exists()
            
            if regional_access:
                return True
                
            # También verificar si tiene membresías activas en esa región
            active_memberships = self.get_active_memberships()
            return active_memberships.filter(region=region).exists()

        return False

    # ========== MÉTODOS ACL ==========
    def get_all_roles(self):
        """Obtiene todos los roles del usuario (primario + adicionales)"""
        roles = []
        if self.primary_role:
            roles.append(self.primary_role)
        roles.extend(self.additional_roles.all())
        return roles

    def has_role(self, role_code):
        """Verifica si el usuario tiene un rol específico"""
        if self.is_superuser:
            return True

        for role in self.get_all_roles():
            if role.code == role_code:
                return True
        return False

    def has_permission_in_module(self, module_code, action_code):
        """Verifica si el usuario tiene un permiso específico en un módulo"""
        if self.is_superuser:
            return True

        for role in self.get_all_roles():
            if role.has_module_action(module_code, action_code):
                return True
        return False

    def get_all_special_permissions(self):
        """Obtiene todos los permisos especiales del usuario"""
        permissions = {}
        for role in self.get_all_roles():
            role_perms = role.get_all_permissions()
            for module_code, actions in role_perms.items():
                if module_code not in permissions:
                    permissions[module_code] = set()
                permissions[module_code].update(actions)

        # Convertir sets a listas
        return {k: list(v) for k, v in permissions.items()}

    def can_access_module(self, module_code):
        """Verifica si el usuario puede acceder a un módulo"""
        if self.is_superuser:
            return True

        from apps.permissions.models import RoleModuleAccess
        for role in self.get_all_roles():
            if RoleModuleAccess.objects.filter(role=role, module__code=module_code).exists():
                return True
        return False

    # ============ MÉTODOS DE SCOPE REGIONAL ============

    def get_regions(self):
        """Obtiene todas las regiones a las que el usuario tiene acceso"""
        from apps.permissions.models import UserRegionalScope

        # Si tiene rol nacional, tiene acceso a todas las regiones
        if self.has_national_access():
            from apps.core.models import PymeMadRegion
            return PymeMadRegion.objects.filter(is_active=True)

        # Obtener regiones específicas asignadas
        scopes = UserRegionalScope.objects.filter(
            user=self,
            is_active=True
        ).select_related('region')

        regions = []
        for scope in scopes:
            if scope.is_valid() and scope.region:
                regions.append(scope.region)

        return regions

    def has_national_access(self):
        """Verifica si el usuario tiene acceso nacional"""
        if self.is_superuser:
            return True

        for role in self.get_all_roles():
            if role.is_national_level() or role.scope in ['national', 'all']:
                return True
        return False

    def has_regional_access(self, region_id=None):
        """Verifica si el usuario tiene acceso a una región específica"""
        if self.has_national_access():
            return True

        if region_id is None:
            # Verificar si tiene acceso a alguna región
            return self.regional_scopes.filter(is_active=True).exists()

        # Verificar acceso a región específica
        from apps.permissions.models import UserRegionalScope
        return UserRegionalScope.objects.filter(
            user=self,
            region_id=region_id,
            is_active=True
        ).exists()

    def get_primary_region(self):
        """Obtiene la región principal del usuario"""
        from apps.permissions.models import UserRegionalScope

        # Si tiene acceso nacional, no tiene región principal específica
        if self.has_national_access():
            return None

        # Buscar región marcada como principal
        try:
            scope = UserRegionalScope.objects.get(
                user=self,
                is_primary=True,
                is_active=True
            )
            if scope.is_valid():
                return scope.region
        except UserRegionalScope.DoesNotExist:
            pass

        # Si no hay región principal, retornar la primera activa
        scope = UserRegionalScope.objects.filter(
            user=self,
            is_active=True
        ).first()

        if scope and scope.is_valid():
            return scope.region

        return None

    def can_manage_user(self, target_user):
        """
        Verifica si puede gestionar a otro usuario basado en jerarquía y scope
        """
        if self.is_superuser:
            return True

        # No puede gestionarse a sí mismo (excepto algunas operaciones)
        if self.id == target_user.id:
            return False

        # Verificar jerarquía de roles
        if self.primary_role and target_user.primary_role:
            self_level = self.primary_role.get_hierarchy_level()
            target_level = target_user.primary_role.get_hierarchy_level()

            # Solo puede gestionar usuarios de menor jerarquía
            if self_level >= target_level:
                return False

        # Verificar scope regional
        if not self.has_national_access():
            # Debe tener acceso a la región del usuario objetivo
            target_region = target_user.get_primary_region()
            if target_region and not self.has_regional_access(target_region.id):
                return False

        return True

    def has_permission_in_module_with_scope(self, module_code, action_code, region_id=None):
        """
        Verifica permisos considerando el scope regional
        """
        # Primero verificar el permiso básico
        if not self.has_permission_in_module(module_code, action_code):
            return False

        # Si se especifica región, verificar acceso regional
        if region_id:
            return self.has_regional_access(region_id)

        return True

    def get_role_display_with_scope(self):
        """
        Obtiene el nombre del rol con información de scope
        """
        if self.is_superuser:
            return "Super Administrador"

        if not self.primary_role:
            return "Sin rol asignado"

        role_name = self.primary_role.name

        # Agregar información de scope
        if self.has_national_access():
            return f"{role_name} (Nacional)"

        primary_region = self.get_primary_region()
        if primary_region:
            return f"{role_name} ({primary_region.name})"

        return role_name

    def get_hierarchy_level(self):
        """
        Obtiene el nivel jerárquico del usuario basado en su rol principal
        """
        if self.is_superuser:
            return 0

        if self.primary_role:
            return self.primary_role.get_hierarchy_level()

        return 999  # Sin rol = menor jerarquía
