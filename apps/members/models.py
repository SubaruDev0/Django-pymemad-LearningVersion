# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from apps.core.constants import REGION_CHOICES
from apps.core.mixins import TimestampedModel
from django.utils import timezone


class Company(TimestampedModel):
    """
    Empresa maderera (puede o no ser socia de PymeMad)
    """
    COMPANY_TYPE = (
        ('sawmill', _('Aserradero')),
        ('manufacturer', _('Manufacturera')),
        ('service', _('Servicios')),
        ('bioenergy', _('Bioenergía')),
        ('construction', _('Construcción en madera')),
        ('other', _('Otro')),
    )

    SIZE_CHOICES = (
        ('micro', _('Microempresa (hasta 2.400 UF)')),
        ('small', _('Pequeña (2.400,01 - 25.000 UF)')),
        ('medium', _('Mediana (25.000,01 - 100.000 UF)')),
        ('large', _('Grande (más de 100.000 UF)')),
    )

    # Información legal
    legal_name = models.CharField(
        max_length=200,
        verbose_name=_('Razón social')
    )
    trade_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Nombre fantasía')
    )
    rut = models.CharField(
        max_length=12,
        unique=True,
        verbose_name=_('RUT empresa')
    )

    # Clasificación
    company_type = models.CharField(
        max_length=20,
        choices=COMPANY_TYPE,
        verbose_name=_('Tipo de empresa')
    )
    size = models.CharField(
        max_length=10,
        choices=SIZE_CHOICES,
        verbose_name=_('Tamaño')
    )

    # Contacto
    email = models.EmailField(verbose_name=_('Email empresa'))
    phone = models.CharField(max_length=20, verbose_name=_('Teléfono'))
    website = models.URLField(blank=True, verbose_name=_('Sitio web'))

    # Ubicación
    address = models.CharField(max_length=200, verbose_name=_('Dirección'))
    city = models.CharField(max_length=100, verbose_name=_('Ciudad'))
    commune = models.CharField(max_length=100, verbose_name=_('Comuna'))
    region = models.CharField(
        max_length=20,
        choices=REGION_CHOICES,
        verbose_name=_('Región')
    )

    # Información operacional
    employee_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Número de empleados')
    )
    annual_revenue_uf = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Ventas anuales (UF)'),
        help_text=_('Para clasificación de tamaño empresa')
    )

    # Productos y servicios
    main_products = models.TextField(
        blank=True,
        verbose_name=_('Productos principales')
    )
    production_capacity = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Capacidad productiva'),
        help_text=_('Ej: 5.000 m³/mes')
    )

    # Certificaciones
    has_fsc = models.BooleanField(default=False, verbose_name=_('Certificación FSC'))
    has_pefc = models.BooleanField(default=False, verbose_name=_('Certificación PEFC'))
    has_iso = models.BooleanField(default=False, verbose_name=_('Certificación ISO'))
    other_certifications = models.TextField(
        blank=True,
        verbose_name=_('Otras certificaciones')
    )

    # Relaciones comerciales
    is_arauco_supplier = models.BooleanField(
        default=False,
        verbose_name=_('Proveedor de Arauco')
    )
    is_cmpc_supplier = models.BooleanField(
        default=False,
        verbose_name=_('Proveedor de CMPC')
    )
    exports = models.BooleanField(
        default=False,
        verbose_name=_('Exporta')
    )
    export_countries = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Países de exportación')
    )

    # Logo
    logo = models.ImageField(
        upload_to='companies/logos/',
        null=True,
        blank=True,
        verbose_name=_('Logo empresa')
    )

    class Meta:
        verbose_name = _("Empresa")
        verbose_name_plural = _("Empresas")
        ordering = ['legal_name']

    def __str__(self):
        return self.trade_name or self.legal_name

    @property
    def display_name(self):
        if self.trade_name:
            return self.trade_name
        return self.legal_name

    def get_size_by_employees(self):
        """Determina el tamaño según número de empleados"""
        if self.employee_count < 10:
            return 'micro'
        elif self.employee_count < 50:
            return 'small'
        elif self.employee_count < 200:
            return 'medium'
        return 'large'  # No debería pasar en PymeMad


class CompanyContact(TimestampedModel):
    """
    Personas de contacto en una empresa
    """
    CONTACT_TYPE = (
        ('owner', _('Dueño/Socio')),
        ('legal_rep', _('Representante Legal')),
        ('manager', _('Gerente')),
        ('admin', _('Administrador')),
        ('sales', _('Ventas')),
        ('operations', _('Operaciones')),
        ('other', _('Otro')),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    person = models.ForeignKey(
        'core.Person',
        on_delete=models.CASCADE,
        related_name='company_contacts'
    )

    contact_type = models.CharField(
        max_length=20,
        choices=CONTACT_TYPE,
        verbose_name=_('Tipo de contacto')
    )
    position = models.CharField(
        max_length=100,
        verbose_name=_('Cargo')
    )

    is_primary = models.BooleanField(
        default=False,
        verbose_name=_('Contacto principal')
    )
    is_authorized = models.BooleanField(
        default=False,
        verbose_name=_('Autorizado para representar'),
        help_text=_('Puede firmar documentos y tomar decisiones')
    )

    # Contacto directo
    direct_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Teléfono directo')
    )
    direct_email = models.EmailField(
        blank=True,
        verbose_name=_('Email directo')
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )

    class Meta:
        verbose_name = _("Contacto de Empresa")
        verbose_name_plural = _("Contactos de Empresa")
        ordering = ['-is_primary', 'contact_type']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='unique_primary_contact_per_company'
            )
        ]

    def __str__(self):
        return f"{self.person.full_name} - {self.position} en {self.company.display_name}"


class Membership(TimestampedModel):
    """
    Membresía de una empresa en una región de PymeMad
    Modelo simplificado que delega información financiera a otros modelos
    """
    STATUS_CHOICES = (
        ('pending', _('Pendiente')),
        ('active', _('Activa')),
        ('suspended', _('Suspendida')),
        ('inactive', _('Inactiva')),
    )

    # Relaciones principales
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='members_memberships'
    )
    region = models.ForeignKey(
        'core.PymeMadRegion',
        on_delete=models.PROTECT,
        related_name='members_memberships'
    )

    # Estado
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )

    # Fechas clave
    application_date = models.DateField(
        auto_now_add=True,
        verbose_name=_('Fecha de solicitud')
    )
    approval_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de aprobación')
    )
    activation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de activación')
    )
    suspension_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de suspensión')
    )

    # Número de socio
    member_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Número de socio'),
        help_text=_('Código único del socio en la región')
    )

    # Documentación
    application_form = models.FileField(
        upload_to='memberships/applications/',
        null=True,
        blank=True,
        verbose_name=_('Formulario de postulación')
    )
    acceptance_letter = models.FileField(
        upload_to='memberships/acceptances/',
        null=True,
        blank=True,
        verbose_name=_('Carta de aceptación')
    )

    # Auditoría
    approved_by = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members_approved',
        verbose_name=_('Aprobado por')
    )

    # Notas
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Notas internas')
    )

    class Meta:
        verbose_name = _("Membresía")
        verbose_name_plural = _("Membresías")
        unique_together = ['company', 'region']
        ordering = ['-activation_date', 'company__legal_name']

    def __str__(self):
        return f"{self.company.display_name} - {self.region.get_code_display()}"

    def save(self, *args, **kwargs):
        # Generar número de socio si no existe
        if not self.member_number and self.status == 'active':
            self.member_number = self.generate_member_number()
        super().save(*args, **kwargs)

    def generate_member_number(self):
        """Genera número único de socio"""
        region_code = self.region.code.split('-')[0][:3].upper()
        year = timezone.now().year

        # Obtener el último número de esa región
        last_member = Membership.objects.filter(
            region=self.region,
            member_number__startswith=f"{region_code}{year}"
        ).order_by('member_number').last()

        if last_member and last_member.member_number:
            last_number = int(last_member.member_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"{region_code}{year}{new_number:04d}"

    @property
    def current_subscription(self):
        """Suscripción activa actual"""
        return self.billing_subscriptions.filter(
            status='active'
        ).order_by('-start_date').first()

    @property
    def is_fee_up_to_date(self):
        """Verifica si está al día con los pagos"""
        if not self.current_subscription:
            return False

        # Verificar si hay órdenes pendientes vencidas
        pending_orders = self.billing_orders.filter(
            status__in=['pending', 'payment_failed'],
            due_date__lt=timezone.now().date()
        ).exists()

        return not pending_orders

    @property
    def has_voting_rights(self):
        """Determina si tiene derecho a voto"""
        if self.status != 'active':
            return False

        # Verificar si está al día con pagos
        if not self.is_fee_up_to_date:
            return False

        # Verificar si su plan incluye voto
        subscription = self.current_subscription
        if subscription and subscription.plan:
            return subscription.plan.includes_voting

        return False

    def activate(self, approved_by=None):
        """Activa la membresía"""
        self.status = 'active'
        self.activation_date = timezone.now().date()
        if approved_by:
            self.approved_by = approved_by
            self.approval_date = timezone.now().date()
        self.save()

    def suspend(self, reason=''):
        """Suspende la membresía"""
        self.status = 'suspended'
        self.suspension_date = timezone.now().date()
        if reason and self.internal_notes:
            self.internal_notes += f"\n\nSUSPENDIDO ({timezone.now().date()}): {reason}"
        elif reason:
            self.internal_notes = f"SUSPENDIDO ({timezone.now().date()}): {reason}"
        self.save()
