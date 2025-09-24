# models.py para la app de gestión del plan estratégico
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

from apps.core.mixins import TimestampedModel
from apps.core.models import Person, PymeMadRegion
from apps.members.models import Membership


class StrategicObjective(TimestampedModel):
    """
    Objetivos estratégicos del plan nacional
    """
    PRIORITY_CHOICES = [
        ('high', _('Alta')),
        ('medium', _('Media')),
        ('low', _('Baja')),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name=_('Título')
    )
    description = models.TextField(
        verbose_name=_('Descripción')
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Prioridad')
    )
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Valor meta')
    )
    measurement_unit = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Unidad de medida')
    )
    start_date = models.DateField(
        verbose_name=_('Fecha de inicio')
    )
    end_date = models.DateField(
        verbose_name=_('Fecha de término')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )

    class Meta:
        verbose_name = _("Objetivo Estratégico")
        verbose_name_plural = _("Objetivos Estratégicos")
        ordering = ['-priority', 'title']

    def __str__(self):
        return self.title


class WorkPlan(TimestampedModel):
    """
    Planes de trabajo regionales alineados con objetivos estratégicos
    """
    STATUS_CHOICES = [
        ('draft', _('Borrador')),
        ('approved', _('Aprobado')),
        ('in_progress', _('En progreso')),
        ('completed', _('Completado')),
        ('cancelled', _('Cancelado')),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name=_('Título')
    )
    region = models.ForeignKey(
        PymeMadRegion,
        on_delete=models.PROTECT,
        related_name='work_plans',
        verbose_name=_('Región')
    )
    strategic_objective = models.ForeignKey(
        StrategicObjective,
        on_delete=models.CASCADE,
        related_name='work_plans',
        verbose_name=_('Objetivo estratégico')
    )
    description = models.TextField(
        verbose_name=_('Descripción')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('Estado')
    )
    year = models.IntegerField(
        verbose_name=_('Año')
    )
    quarter = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        null=True,
        blank=True,
        verbose_name=_('Trimestre')
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Presupuesto')
    )
    responsible = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        related_name='responsible_work_plans',
        verbose_name=_('Responsable')
    )
    created_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_work_plans',
        verbose_name=_('Creado por')
    )

    class Meta:
        verbose_name = _("Plan de Trabajo")
        verbose_name_plural = _("Planes de Trabajo")
        ordering = ['-year', '-quarter', 'region', 'title']
        unique_together = ['region', 'year', 'quarter', 'title']

    def __str__(self):
        return f"{self.title} - {self.region.name} ({self.year})"


class Activity(TimestampedModel):
    """
    Actividades específicas dentro de los planes de trabajo
    """
    TYPE_CHOICES = [
        ('training', _('Capacitación')),
        ('meeting', _('Reunión')),
        ('event', _('Evento')),
        ('project', _('Proyecto')),
        ('publication', _('Publicación')),
        ('inspection', _('Inspección')),
        ('certification', _('Certificación')),
        ('other', _('Otro')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pendiente')),
        ('in_progress', _('En progreso')),
        ('completed', _('Completado')),
        ('cancelled', _('Cancelado')),
        ('overdue', _('Vencido')),
    ]

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name=_('UUID')
    )
    work_plan = models.ForeignKey(
        WorkPlan,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name=_('Plan de trabajo')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Título')
    )
    description = models.TextField(
        verbose_name=_('Descripción')
    )
    activity_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_('Tipo de actividad')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )
    start_date = models.DateField(
        verbose_name=_('Fecha de inicio')
    )
    end_date = models.DateField(
        verbose_name=_('Fecha de término')
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Ubicación')
    )
    responsible = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        related_name='responsible_activities',
        verbose_name=_('Responsable')
    )
    participants_target = models.IntegerField(
        default=0,
        verbose_name=_('Participantes objetivo')
    )
    participants_actual = models.IntegerField(
        default=0,
        verbose_name=_('Participantes reales')
    )
    budget_allocated = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Presupuesto asignado')
    )
    budget_executed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Presupuesto ejecutado')
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Progreso (%)')
    )

    # Campos específicos para ciertos tipos de actividades
    related_company = models.ForeignKey(
        'members.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name=_('Empresa relacionada'),
        help_text=_('Para reuniones con grandes empresas')
    )

    class Meta:
        verbose_name = _("Actividad")
        verbose_name_plural = _("Actividades")
        ordering = ['start_date', 'title']

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Actualizar estado automáticamente si está vencido
        if self.end_date < timezone.now().date() and self.status not in ['completed', 'cancelled']:
            self.status = 'overdue'
        super().save(*args, **kwargs)


class ActivityEvidence(TimestampedModel):
    """
    Evidencias y documentación de actividades realizadas
    """
    EVIDENCE_TYPE_CHOICES = [
        ('photo', _('Fotografía')),
        ('document', _('Documento')),
        ('list', _('Lista de asistencia')),
        ('report', _('Informe')),
        ('invoice', _('Factura')),
        ('agreement', _('Acuerdo/Convenio')),
        ('other', _('Otro')),
    ]

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='evidences',
        verbose_name=_('Actividad')
    )
    evidence_type = models.CharField(
        max_length=20,
        choices=EVIDENCE_TYPE_CHOICES,
        verbose_name=_('Tipo de evidencia')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Título')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    file = models.FileField(
        upload_to='strategic_plan/evidence/%Y/%m/',
        verbose_name=_('Archivo')
    )
    uploaded_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Subido por')
    )

    class Meta:
        verbose_name = _("Evidencia de Actividad")
        verbose_name_plural = _("Evidencias de Actividades")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.activity.title}"


class KeyPerformanceIndicator(TimestampedModel):
    """
    Indicadores clave de desempeño (KPIs) para medir objetivos
    """
    FREQUENCY_CHOICES = [
        ('monthly', _('Mensual')),
        ('quarterly', _('Trimestral')),
        ('semiannual', _('Semestral')),
        ('annual', _('Anual')),
    ]

    strategic_objective = models.ForeignKey(
        StrategicObjective,
        on_delete=models.CASCADE,
        related_name='kpis',
        verbose_name=_('Objetivo estratégico')
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_('Nombre')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    measurement_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='monthly',
        verbose_name=_('Frecuencia de medición')
    )
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Valor objetivo')
    )
    unit = models.CharField(
        max_length=50,
        verbose_name=_('Unidad de medida')
    )
    calculation_method = models.TextField(
        blank=True,
        verbose_name=_('Método de cálculo'),
        help_text=_('Descripción de cómo se calcula este indicador')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )

    class Meta:
        verbose_name = _("Indicador Clave de Desempeño")
        verbose_name_plural = _("Indicadores Clave de Desempeño")
        ordering = ['strategic_objective', 'name']

    def __str__(self):
        return f"{self.name} - {self.strategic_objective.title}"


class KPIMeasurement(TimestampedModel):
    """
    Mediciones periódicas de los KPIs
    """
    kpi = models.ForeignKey(
        KeyPerformanceIndicator,
        on_delete=models.CASCADE,
        related_name='measurements',
        verbose_name=_('KPI')
    )
    region = models.ForeignKey(
        PymeMadRegion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Región'),
        help_text=_('Dejar en blanco para mediciones nacionales')
    )
    period_date = models.DateField(
        verbose_name=_('Fecha del período')
    )
    actual_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Valor real')
    )
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Valor objetivo')
    )
    compliance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(999.99)],
        verbose_name=_('Porcentaje de cumplimiento')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )
    measured_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Medido por')
    )

    class Meta:
        verbose_name = _("Medición de KPI")
        verbose_name_plural = _("Mediciones de KPI")
        ordering = ['-period_date', 'kpi']
        unique_together = ['kpi', 'region', 'period_date']

    def __str__(self):
        region_name = self.region.name if self.region else "Nacional"
        return f"{self.kpi.name} - {region_name} - {self.period_date}"

    def save(self, *args, **kwargs):
        # Calcular porcentaje de cumplimiento automáticamente
        if self.target_value > 0:
            self.compliance_percentage = (self.actual_value / self.target_value) * 100
        super().save(*args, **kwargs)


class ActivityParticipant(TimestampedModel):
    """
    Registro de participantes en actividades
    """
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_('Actividad')
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_participations',
        verbose_name=_('Membresía')
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_participations',
        verbose_name=_('Persona')
    )
    external_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Nombre (externo)'),
        help_text=_('Para participantes no registrados en el sistema')
    )
    external_company = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Empresa (externa)')
    )
    attendance = models.BooleanField(
        default=True,
        verbose_name=_('Asistió')
    )

    class Meta:
        verbose_name = _("Participante de Actividad")
        verbose_name_plural = _("Participantes de Actividades")
        ordering = ['activity', 'person__last_name']

    def __str__(self):
        if self.person:
            return f"{self.person.full_name} - {self.activity.title}"
        return f"{self.external_name} - {self.activity.title}"


class ActivityComment(TimestampedModel):
    """
    Comentarios y seguimiento de actividades
    """
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Actividad')
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Autor')
    )
    comment = models.TextField(
        verbose_name=_('Comentario')
    )
    is_internal = models.BooleanField(
        default=False,
        verbose_name=_('Comentario interno'),
        help_text=_('Los comentarios internos solo son visibles para el equipo')
    )

    class Meta:
        verbose_name = _("Comentario de Actividad")
        verbose_name_plural = _("Comentarios de Actividades")
        ordering = ['-created_at']

    def __str__(self):
        return f"Comentario en {self.activity.title} por {self.author.full_name if self.author else 'Anónimo'}"


class StrategicPlanReport(TimestampedModel):
    """
    Reportes periódicos del plan estratégico
    """
    REPORT_TYPE_CHOICES = [
        ('monthly', _('Mensual')),
        ('quarterly', _('Trimestral')),
        ('semiannual', _('Semestral')),
        ('annual', _('Anual')),
        ('special', _('Especial')),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name=_('Título')
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name=_('Tipo de reporte')
    )
    period_start = models.DateField(
        verbose_name=_('Inicio del período')
    )
    period_end = models.DateField(
        verbose_name=_('Fin del período')
    )
    region = models.ForeignKey(
        PymeMadRegion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='strategic_reports',
        verbose_name=_('Región'),
        help_text=_('Dejar en blanco para reportes nacionales')
    )
    executive_summary = models.TextField(
        verbose_name=_('Resumen ejecutivo')
    )
    file = models.FileField(
        upload_to='strategic_plan/reports/%Y/',
        null=True,
        blank=True,
        verbose_name=_('Archivo del reporte')
    )
    generated_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Generado por')
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name=_('Publicado')
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de publicación')
    )

    class Meta:
        verbose_name = _("Reporte del Plan Estratégico")
        verbose_name_plural = _("Reportes del Plan Estratégico")
        ordering = ['-period_end', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.period_start} a {self.period_end}"
