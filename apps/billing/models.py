# models/payments.py
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

from apps.core.mixins import TimestampedModel


class MembershipPlan(TimestampedModel):
    """
    Planes de membresía/cuotas para PymeMad
    Permite diferentes esquemas de pago por región o categoría
    """
    BILLING_PERIOD_CHOICES = [
        ('monthly', _('Mensual')),
        ('quarterly', _('Trimestral')),
        ('semiannual', _('Semestral')),
        ('annual', _('Anual')),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre del plan')
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Código'),
        help_text=_('Identificador único del plan')
    )

    # Configuración regional
    region = models.ForeignKey(
        'core.PymeMadRegion',
        on_delete=models.CASCADE,
        related_name='membership_plans',
        verbose_name=_('Región')
    )

    # Criterios de aplicación
    company_size = models.CharField(
        max_length=10,
        choices=[
            ('all', _('Todas')),
            ('micro', _('Microempresa')),
            ('small', _('Pequeña')),
            ('medium', _('Mediana')),
            ('large', _('Grande')),
        ],
        default='all',
        verbose_name=_('Tamaño de empresa')
    )

    # Montos por período
    monthly_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_('Monto mensual')
    )
    quarterly_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Monto trimestral')
    )
    semiannual_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Monto semestral')
    )
    annual_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Monto anual')
    )

    # Beneficios incluidos
    includes_magazine = models.BooleanField(
        default=True,
        verbose_name=_('Incluye revista')
    )
    includes_voting = models.BooleanField(
        default=True,
        verbose_name=_('Incluye derecho a voto')
    )
    includes_events = models.BooleanField(
        default=True,
        verbose_name=_('Incluye eventos')
    )

    # Estado
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Plan por defecto')
    )

    # Validez
    valid_from = models.DateField(
        verbose_name=_('Válido desde')
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Válido hasta')
    )

    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )

    class Meta:
        verbose_name = _("Plan de Membresía")
        verbose_name_plural = _("Planes de Membresía")
        constraints = [
            models.UniqueConstraint(
                fields=['region', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_plan_per_region'
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.region.get_code_display()}"

    def get_amount_for_period(self, billing_period):
        """Obtiene el monto según el período de facturación"""
        period_map = {
            'monthly': self.monthly_amount,
            'quarterly': self.quarterly_amount or self.monthly_amount * 3,
            'semiannual': self.semiannual_amount or self.monthly_amount * 6,
            'annual': self.annual_amount or self.monthly_amount * 12,
        }
        return period_map.get(billing_period, self.monthly_amount)


class MembershipSubscription(TimestampedModel):
    """
    Suscripción activa de una empresa a un plan de membresía
    """
    STATUS_CHOICES = [
        ('active', _('Activa')),
        ('suspended', _('Suspendida')),
        ('cancelled', _('Cancelada')),
        ('expired', _('Expirada')),
    ]

    BILLING_PERIOD_CHOICES = [
        ('monthly', _('Mensual')),
        ('quarterly', _('Trimestral')),
        ('semiannual', _('Semestral')),
        ('annual', _('Anual')),
    ]

    membership = models.ForeignKey(
        'members.Membership',
        on_delete=models.PROTECT,
        related_name='billing_subscriptions',
        verbose_name=_('Membresía')
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name=_('Plan')
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Estado')
    )
    billing_period = models.CharField(
        max_length=20,
        choices=BILLING_PERIOD_CHOICES,
        default='monthly',
        verbose_name=_('Período de facturación')
    )

    # Fechas
    start_date = models.DateField(
        verbose_name=_('Fecha de inicio')
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de término')
    )
    next_billing_date = models.DateField(
        verbose_name=_('Próxima fecha de cobro')
    )

    # Montos
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Monto a cobrar'),
        help_text=_('Monto según el período seleccionado')
    )

    # Control de cobros
    auto_renew = models.BooleanField(
        default=True,
        verbose_name=_('Renovación automática')
    )
    payment_retries = models.IntegerField(
        default=0,
        verbose_name=_('Intentos de cobro fallidos')
    )
    last_payment_attempt = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Último intento de cobro')
    )

    # Cancelación
    cancellation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de cancelación')
    )
    cancellation_reason = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Razón de cancelación')
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )

    class Meta:
        verbose_name = _("Suscripción de Membresía")
        verbose_name_plural = _("Suscripciones de Membresía")
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.membership} - {self.plan.name} ({self.status})"

    def calculate_next_billing_date(self):
        """Calcula la próxima fecha de cobro"""
        if self.billing_period == 'monthly':
            return self.next_billing_date + relativedelta(months=1)
        elif self.billing_period == 'quarterly':
            return self.next_billing_date + relativedelta(months=3)
        elif self.billing_period == 'semiannual':
            return self.next_billing_date + relativedelta(months=6)
        elif self.billing_period == 'annual':
            return self.next_billing_date + relativedelta(years=1)
        return None

    def save(self, *args, **kwargs):
        if not self.amount:
            self.amount = self.plan.get_amount_for_period(self.billing_period)
        super().save(*args, **kwargs)


class Order(TimestampedModel):
    """
    Orden de pago unificada para PymeMad
    """
    ORDER_TYPE_CHOICES = [
        ('membership_fee', _('Cuota de Membresía')),
        ('event', _('Evento')),
        ('magazine_ad', _('Publicidad Revista')),
        ('other', _('Otro')),
    ]

    ORDER_STATUS_CHOICES = [
        ('pending', _('Pendiente')),
        ('payment_processing', _('Procesando Pago')),
        ('payment_failed', _('Pago Fallido')),
        ('paid', _('Pagado')),
        ('cancelled', _('Cancelado')),
        ('refunded', _('Reembolsado')),
        ('completed', _('Completado')),
    ]

    # Identificación
    order_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_('ID de orden')
    )
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        verbose_name=_('Tipo de orden')
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )

    # Relaciones
    membership = models.ForeignKey(
        'members.Membership',
        on_delete=models.PROTECT,
        related_name='billing_orders',
        verbose_name='Membresía'
    )
    subscription = models.ForeignKey(
        MembershipSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name=_('Suscripción'),
        help_text=_('Para órdenes de cuotas periódicas')
    )

    # Montos
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Subtotal')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('IVA')
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Descuento')
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Total a pagar')
    )

    # Fechas
    issue_date = models.DateField(
        default=timezone.now,
        verbose_name=_('Fecha de emisión')
    )
    due_date = models.DateField(
        verbose_name=_('Fecha de vencimiento')
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de pago')
    )

    # Información adicional
    description = models.TextField(
        verbose_name=_('Descripción')
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Notas internas')
    )

    # Facturación
    requires_invoice = models.BooleanField(
        default=True,
        verbose_name=_('Requiere factura')
    )

    class Meta:
        verbose_name = _("Orden de Pago")
        verbose_name_plural = _("Órdenes de Pago")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_type', 'status']),
            models.Index(fields=['membership']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.order_id} - {self.membership.company.display_name}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self.generate_order_id()

        # Calcular total
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

        super().save(*args, **kwargs)

    def generate_order_id(self):
        """Genera un ID único para la orden"""
        prefix = 'PM'  # PymeMad
        date_part = timezone.now().strftime('%Y%m')

        while True:
            random_part = uuid.uuid4().hex[:6].upper()
            order_id = f"{prefix}{date_part}{random_part}"
            if not Order.objects.filter(order_id=order_id).exists():
                return order_id


class OrderItem(TimestampedModel):
    """
    Items individuales de una orden
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Orden')
    )

    description = models.CharField(
        max_length=255,
        verbose_name=_('Descripción')
    )

    # Período que cubre (para cuotas)
    period_start = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Período desde')
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Período hasta')
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        verbose_name=_('Cantidad')
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Precio unitario')
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('% Descuento')
    )

    class Meta:
        verbose_name = _("Item de Orden")
        verbose_name_plural = _("Items de Orden")
        ordering = ['id']

    def __str__(self):
        return f"{self.description} - {self.order.order_id}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def discount_amount(self):
        return (self.subtotal * self.discount_percentage) / Decimal('100')

    @property
    def total(self):
        return self.subtotal - self.discount_amount


class Payment(TimestampedModel):
    """
    Registro de pagos realizados
    """
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', _('Transferencia Bancaria')),
        ('check', _('Cheque')),
        ('cash', _('Efectivo')),
        ('credit_card', _('Tarjeta de Crédito')),
        ('debit_card', _('Tarjeta de Débito')),
        ('webpay', _('WebPay')),
        ('other', _('Otro')),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', _('Pendiente')),
        ('processing', _('Procesando')),
        ('completed', _('Completado')),
        ('failed', _('Fallido')),
        ('reversed', _('Reversado')),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('Orden')
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name=_('Método de pago')
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Monto')
    )

    payment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Fecha de pago')
    )

    # Referencia externa
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Número de referencia'),
        help_text=_('Número de transferencia, cheque, etc.')
    )

    # Para pagos electrónicos
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('ID de transacción')
    )
    authorization_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Código de autorización')
    )

    # Información adicional
    payer_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Nombre del pagador')
    )
    payer_rut = models.CharField(
        max_length=12,
        blank=True,
        verbose_name=_('RUT del pagador')
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )

    # Auditoría
    registered_by = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments_registered',
        verbose_name=_('Registrado por')
    )

    class Meta:
        verbose_name = _("Pago")
        verbose_name_plural = _("Pagos")
        ordering = ['-payment_date']

    def __str__(self):
        return f"Pago {self.amount} - {self.order.order_id}"
