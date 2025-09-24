# models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from .mixins import TimestampedModel
from .constants import REGION_CHOICES
from ..accounts.models import User


class Person(TimestampedModel):
    """
    Modelo base para cualquier persona en el sistema
    Puede ser un socio (Member) o un externo
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='person_profile'
    )

    # Información básica
    first_name = models.CharField(max_length=100, verbose_name=_('Nombres'))
    last_name = models.CharField(max_length=100, verbose_name=_('Apellidos'))
    rut = models.CharField(max_length=12, unique=True, verbose_name=_('RUT'))
    email = models.EmailField(verbose_name=_('Email'))
    phone = models.CharField(max_length=20, verbose_name=_('Teléfono'))

    # Perfil
    photo = models.ImageField(
        upload_to='people/photos/',
        null=True,
        blank=True,
        verbose_name=_('Foto')
    )
    linkedin_url = models.URLField(blank=True, verbose_name=_('LinkedIn'))
    bio = models.TextField(blank=True, verbose_name=_('Biografía'))

    # Tipo de persona
    is_member = models.BooleanField(
        default=True,
        verbose_name=_('Es socio'),
        help_text=_('False para consultores, asesores externos')
    )

    class Meta:
        verbose_name = _("Persona")
        verbose_name_plural = _("Personas")
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class BoardPosition(TimestampedModel):
    """
    Cargo en un directorio (nacional o regional)
    """
    POSITION_TYPES = (
        # Cargos principales
        ('president', _('Presidente')),
        ('vicepresident', _('Vicepresidente')),
        ('secretary', _('Secretario')),
        ('treasurer', _('Tesorero')),
        ('director', _('Director')),
        # Cargos especiales/externos
        ('coordinator', _('Coordinador')),
        ('manager', _('Gerente')),
        ('advisor', _('Asesor')),
    )

    BOARD_LEVEL = (
        ('national', _('Nacional')),
        ('regional', _('Regional')),
    )

    # Persona que ocupa el cargo
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name='board_positions'
    )

    # Tipo y nivel del cargo
    position = models.CharField(
        max_length=30,
        choices=POSITION_TYPES,
        verbose_name=_('Cargo')
    )
    level = models.CharField(
        max_length=10,
        choices=BOARD_LEVEL,
        verbose_name=_('Nivel')
    )

    # Si es regional, a qué región
    region = models.ForeignKey(
        'PymeMadRegion',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='board_positions',
        verbose_name=_('Región')
    )

    # Período
    start_date = models.DateField(verbose_name=_('Fecha inicio'))
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha término')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )

    # Orden para mostrar en template
    display_order = models.IntegerField(
        default=0,
        verbose_name=_('Orden de visualización'),
        help_text=_('Menor número aparece primero')
    )

    class Meta:
        verbose_name = _("Cargo Directivo")
        verbose_name_plural = _("Cargos Directivos")
        ordering = ['level', 'display_order', 'position']
        constraints = [
            # Solo un presidente activo por nivel/región
            models.UniqueConstraint(
                fields=['level', 'region', 'position'],
                condition=models.Q(is_active=True, position='president'),
                name='unique_president_per_board'
            ),
            # Validar que regional tenga región
            models.CheckConstraint(
                check=(
                        models.Q(level='national', region__isnull=True) |
                        models.Q(level='regional', region__isnull=False)
                ),
                name='regional_must_have_region'
            )
        ]

    def __str__(self):
        if self.level == 'national':
            return f"{self.person.full_name} - {self.get_position_display()} Nacional"
        else:
            return f"{self.person.full_name} - {self.get_position_display()} {self.region.get_code_display()}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.level == 'regional' and not self.region:
            raise ValidationError('Los cargos regionales deben especificar una región')
        if self.level == 'national' and self.region:
            raise ValidationError('Los cargos nacionales no deben tener región')


# Ajuste a PymeMadRegion para simplificar
class PymeMadRegion(TimestampedModel):
    """Asociación Gremial Regional"""
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    code = models.CharField(
        max_length=20,
        choices=REGION_CHOICES,
        unique=True,
        verbose_name=_('Código')
    )
    rut = models.CharField(max_length=12, unique=True, verbose_name=_('RUT'))

    # Información de contacto
    email = models.EmailField(verbose_name=_('Email'))
    phone = models.CharField(max_length=20, verbose_name=_('Teléfono'))
    address = models.CharField(max_length=200, verbose_name=_('Dirección'))
    city = models.CharField(max_length=100, verbose_name=_('Ciudad'))

    # Estado
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    founded_date = models.DateField(null=True, blank=True, verbose_name=_('Fecha de fundación'))

    class Meta:
        verbose_name = _("Región PymeMad")
        verbose_name_plural = _("Regiones PymeMad")
        ordering = ['name']

    def __str__(self):
        return f"PymeMad {self.get_code_display()}"

    def get_current_board(self):
        """Obtiene el directorio actual de la región"""
        return self.board_positions.filter(
            is_active=True,
            level='regional'
        ).select_related('person')

    @property
    def current_president(self):
        """Presidente actual de la región"""
        return self.board_positions.filter(
            is_active=True,
            position='president'
        ).select_related('person').first()
