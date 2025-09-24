# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords
from apps.core.mixins import TimestampedModel



class User(AbstractUser, TimestampedModel):
    """
    Usuario del sistema - Solo datos personales
    La información empresarial está en Member
    La relación con regiones está en PymeMadMembership
    """
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
