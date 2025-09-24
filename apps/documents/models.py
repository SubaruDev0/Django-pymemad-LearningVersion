# models/documents.py
from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.mixins import TimestampedModel
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import os
import uuid


class DocumentCategory(TimestampedModel):
    """
    Categorías de documentos para organización
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Nombre')
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Código')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activa')
    )

    class Meta:
        verbose_name = _("Categoría de Documento")
        verbose_name_plural = _("Categorías de Documentos")
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(TimestampedModel):
    """
    Sistema centralizado de gestión documental
    """
    DOCUMENT_TYPE_CHOICES = [
        # Documentos legales/estatutarios
        ('statutes', _('Estatutos')),
        ('statutes_update', _('Actualización de Estatutos')),
        ('incorporation_act', _('Acta de Constitución')),
        ('legal_personality', _('Personalidad Jurídica')),

        # Actas
        ('assembly_minutes', _('Acta de Asamblea')),
        ('board_minutes', _('Acta de Directorio')),
        ('election_minutes', _('Acta de Elección')),

        # Documentos financieros
        ('financial_statement', _('Estado Financiero')),
        ('audit_report', _('Informe de Auditoría')),
        ('budget', _('Presupuesto')),

        # Documentos de membresía
        ('membership_application', _('Solicitud de Membresía')),
        ('membership_acceptance', _('Carta de Aceptación')),
        ('power_of_attorney', _('Poder de Representación')),

        # Documentos de pago
        ('invoice', _('Factura')),
        ('receipt', _('Recibo')),
        ('payment_proof', _('Comprobante de Pago')),

        # Proyectos y postulaciones
        ('project_proposal', _('Propuesta de Proyecto')),
        ('fund_application', _('Postulación a Fondos')),
        ('project_report', _('Informe de Proyecto')),

        # Comunicaciones
        ('official_letter', _('Carta Oficial')),
        ('agreement', _('Convenio/Acuerdo')),
        ('contract', _('Contrato')),

        # Otros
        ('magazine_edition', _('Edición Revista')),
        ('presentation', _('Presentación')),
        ('other', _('Otro')),
    ]

    PRIVACY_LEVELS = [
        ('public', _('Público')),
        ('members', _('Solo Socios')),
        ('board', _('Solo Directorio')),
        ('admin', _('Solo Administradores')),
    ]

    # Identificación
    document_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name=_('ID Documento')
    )

    title = models.CharField(
        max_length=200,
        verbose_name=_('Título')
    )
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
        verbose_name=_('Tipo de documento')
    )
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name=_('Categoría')
    )

    # Archivo
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png']
            )
        ],
        verbose_name=_('Archivo')
    )
    file_size = models.BigIntegerField(
        editable=False,
        verbose_name=_('Tamaño (bytes)')
    )
    file_hash = models.CharField(
        max_length=64,
        editable=False,
        verbose_name=_('Hash del archivo'),
        help_text=_('Para verificar integridad')
    )

    # Metadatos
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    document_date = models.DateField(
        verbose_name=_('Fecha del documento'),
        help_text=_('Fecha que aparece en el documento')
    )
    expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de vencimiento')
    )

    # Privacidad y acceso
    privacy_level = models.CharField(
        max_length=10,
        choices=PRIVACY_LEVELS,
        default='admin',
        verbose_name=_('Nivel de privacidad')
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name=_('Publicado')
    )

    # Relación genérica (puede asociarse a cualquier modelo)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # Específicas (para relaciones comunes)
    region = models.ForeignKey(
        'core.PymeMadRegion',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('Región')
    )
    membership = models.ForeignKey(
        'members.Membership',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('Membresía')
    )

    # Versioning
    version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name=_('Versión')
    )
    replaces = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replaced_by',
        verbose_name=_('Reemplaza a')
    )

    # Auditoría
    uploaded_by = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        related_name='documents_uploaded',
        verbose_name=_('Subido por')
    )
    verified = models.BooleanField(
        default=False,
        verbose_name=_('Verificado')
    )
    verified_by = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_verified',
        verbose_name=_('Verificado por')
    )
    verified_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de verificación')
    )

    # Tags para búsqueda
    tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Etiquetas'),
        help_text=_('Separadas por comas')
    )

    # Control
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )

    # Contador de descargas simple
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Número de descargas')
    )

    class Meta:
        verbose_name = _("Documento")
        verbose_name_plural = _("Documentos")
        ordering = ['-document_date', '-created_at']
        indexes = [
            models.Index(fields=['document_type', 'is_active']),
            models.Index(fields=['region', 'privacy_level']),
            models.Index(fields=['document_date']),
        ]
        permissions = [
            ("verify_document", _("Can verify documents")),
            ("view_private_document", _("Can view private documents")),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"

    def save(self, *args, **kwargs):
        # Generar document_id si no existe
        if not self.document_id:
            self.document_id = self.generate_document_id()

        # Calcular tamaño del archivo
        if self.file and not self.file_size:
            self.file_size = self.file.size

        # Calcular hash del archivo
        if self.file and not self.file_hash:
            self.file_hash = self.calculate_file_hash()

        super().save(*args, **kwargs)

    def generate_document_id(self):
        """Genera ID único para el documento"""
        prefix = self.document_type[:3].upper()
        year = timezone.now().year
        random = uuid.uuid4().hex[:6].upper()
        return f"{prefix}{year}{random}"

    def calculate_file_hash(self):
        """Calcula hash SHA256 del archivo"""
        import hashlib
        sha256_hash = hashlib.sha256()
        if self.file:
            for chunk in self.file.chunks():
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    @property
    def file_extension(self):
        """Obtiene la extensión del archivo"""
        return os.path.splitext(self.file.name)[1]

    @property
    def is_expired(self):
        """Verifica si el documento está vencido"""
        if not self.expiration_date:
            return False
        return self.expiration_date < timezone.now().date()

    def can_view(self, user):
        """Determina si un usuario puede ver el documento"""
        if not user.is_authenticated:
            return self.privacy_level == 'public'

        if user.is_superuser or user.is_staff:
            return True

        # Lógica según privacy_level
        if self.privacy_level == 'public':
            return True

        # Verificar si el usuario tiene membresía activa
        person = getattr(user, 'person_profile', None)
        if not person:
            return False

        if self.privacy_level == 'members':
            # Verificar si tiene membresía activa en alguna región
            return person.company_contacts.filter(
                company__members_memberships__status='active'
            ).exists()

        if self.privacy_level == 'board':
            # Verificar si tiene cargo directivo
            return person.board_positions.filter(
                is_active=True
            ).exists()

        return False


# Configuración inicial de categorías
INITIAL_CATEGORIES = [
    {'name': 'Legal', 'code': 'legal', 'description': 'Documentos legales y estatutarios'},
    {'name': 'Actas', 'code': 'minutes', 'description': 'Actas de reuniones y asambleas'},
    {'name': 'Financiero', 'code': 'financial', 'description': 'Documentos financieros y contables'},
    {'name': 'Membresía', 'code': 'membership', 'description': 'Documentos de socios'},
    {'name': 'Proyectos', 'code': 'projects', 'description': 'Proyectos y postulaciones'},
    {'name': 'Comunicaciones', 'code': 'communications', 'description': 'Cartas y comunicados'},
    {'name': 'Revista', 'code': 'magazine', 'description': 'Ediciones de la revista'},
]
