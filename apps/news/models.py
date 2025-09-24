from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.mixins import TimestampedModel

class NewsSource(TimestampedModel):
    name = models.CharField(max_length=100, unique=True)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Fuente de Noticias")
        verbose_name_plural = _("Fuentes de Noticias")

class News(models.Model):
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE, related_name='news')
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000, unique=True)  # Aumentado de 200 default
    content = models.TextField(blank=True)
    excerpt = models.TextField(blank=True)
    published_date = models.DateTimeField(null=True, blank=True)
    scraped_date = models.DateTimeField(default=timezone.now)
    image_url = models.URLField(blank=True, null=True)
    author = models.CharField(max_length=200, blank=True)
    is_pymemad_related = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.source.name}: {self.title}"
    
    class Meta:
        verbose_name = _("Noticia")
        verbose_name_plural = _("Noticias")
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['url']),
            models.Index(fields=['source', '-published_date']),
        ]

class ScrapingLog(TimestampedModel):
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE)
    finished_at = models.DateTimeField(null=True, blank=True)
    news_found = models.IntegerField(default=0)
    news_saved = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('running', _('En proceso')),
        ('completed', _('Completado')),
        ('failed', _('Fallido')),
    ], default='running')
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.source.name} - {self.created_at}"
    
    class Meta:
        verbose_name = _("Log de Scraping")
        verbose_name_plural = _("Logs de Scraping")
        ordering = ['-created_at']
