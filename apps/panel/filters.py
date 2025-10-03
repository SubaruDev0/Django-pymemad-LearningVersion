"""
Filtros específicos para el panel de administración
Este módulo contiene los filtros utilizados en las vistas del panel
"""

import django_filters
from django import forms
from django.db.models import Q
from django.utils.dateparse import parse_date
from django_filters import ChoiceFilter, ModelChoiceFilter, CharFilter

from apps.accounts.models import User
from apps.landing.models import Post, Category, Tag, Comment
from apps.landing.models import ContactMessage  # nuevo import


# =====================================================================
# FILTROS DE POSTS/NOTICIAS
# =====================================================================

class PostFilter(django_filters.FilterSet):
    """
    Filtro para filtrar publicaciones por rango de fechas, estado, categoría y autor.
    """
    status = ChoiceFilter(
        choices=(
            ('DRAFT', 'Borrador'),
            ('PUBLISHED', 'Publicado')
        ),
        label="Estado",
        widget=forms.Select(attrs={'class': 'form-control select2-status'})
    )
    category = ModelChoiceFilter(
        queryset=Category.objects.all(),
        label="Categoría",
        widget=forms.Select(attrs={'class': 'form-control select2-category'})
    )
    author = ModelChoiceFilter(
        queryset=User.objects.filter(blog_posts__isnull=False, is_superuser=True).distinct(),
        label="Autor",
        widget=forms.Select(attrs={'class': 'form-control select2-author'})
    )
    created_date_range = CharFilter(
        label='Rango de Fechas',
        method='filter_by_date_range',
        widget=forms.TextInput(attrs={
            'class': 'form-control flatpickr-input',
            'placeholder': 'Seleccionar rango de fechas',
            'autocomplete': 'off'
        })
    )

    def filter_by_date_range(self, queryset, name, value):
        print(f"Filtrando por rango de fechas: {value}")
        if not value:
            return queryset

        try:
            # Divide el rango en inicio y fin
            start_date, end_date = value.split(' a ')
            start_date = parse_date(start_date.strip())
            end_date = parse_date(end_date.strip())
            if not start_date or not end_date:
                return queryset

            # Aplica el filtro usando created__date
            return queryset.filter(created_at__date__range=(start_date, end_date))
        except (ValueError, IndexError):
            return queryset

    class Meta:
        model = Post
        fields = ['status', 'category', 'author', 'created_date_range']


# =====================================================================
# FILTROS DE CATEGORÍAS
# =====================================================================

class CategoryFilter(django_filters.FilterSet):
    """
    Filtro para filtrar categorías por nombre y rango de fechas.
    """
    name = CharFilter(
        label='Nombre',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre'
        })
    )

    created_date_range = CharFilter(
        label='Rango de Fechas',
        method='filter_by_date_range',
        widget=forms.TextInput(attrs={
            'class': 'form-control flatpickr-input',
            'placeholder': 'Seleccionar rango de fechas',
            'autocomplete': 'off'
        })
    )

    def filter_by_date_range(self, queryset, name, value):
        if not value:
            return queryset

        try:
            # Divide el rango en inicio y fin
            start_date, end_date = value.split(' a ')
            start_date = parse_date(start_date.strip())
            end_date = parse_date(end_date.strip())
            if not start_date or not end_date:
                return queryset

            # Aplica el filtro usando created_at__date
            return queryset.filter(created_at__date__range=(start_date, end_date))
        except (ValueError, IndexError):
            return queryset

    class Meta:
        model = Category
        fields = ['name', 'created_date_range']


# =====================================================================
# FILTROS DE ETIQUETAS (TAGS)
# =====================================================================

class TagFilter(django_filters.FilterSet):
    """
    Filtro para filtrar tags por nombre y rango de fechas.
    """
    name = CharFilter(
        label='Nombre',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre'
        })
    )

    created_date_range = CharFilter(
        label='Rango de Fechas',
        method='filter_by_date_range',
        widget=forms.TextInput(attrs={
            'class': 'form-control flatpickr-input',
            'placeholder': 'Seleccionar rango de fechas',
            'autocomplete': 'off'
        })
    )

    def filter_by_date_range(self, queryset, name, value):
        if not value:
            return queryset

        try:
            # Divide el rango en inicio y fin
            start_date, end_date = value.split(' a ')
            start_date = parse_date(start_date.strip())
            end_date = parse_date(end_date.strip())
            if not start_date or not end_date:
                return queryset

            # Aplica el filtro usando created_at__date
            return queryset.filter(created_at__date__range=(start_date, end_date))
        except (ValueError, IndexError):
            return queryset

    class Meta:
        model = Tag
        fields = ['name', 'created_date_range']


# =====================================================================
# FILTROS DE COMENTARIOS
# =====================================================================

class CommentFilter(django_filters.FilterSet):
    """
    Filtro para filtrar comentarios por estado, post y rango de fechas.
    """
    active = ChoiceFilter(
        choices=(
            (True, 'Publicados'),
            (False, 'Pendientes')
        ),
        label="Estado",
        widget=forms.Select(attrs={'class': 'form-control select2-status'}),
        empty_label="Todos los estados"
    )

    post = ModelChoiceFilter(
        queryset=Post.objects.all(),
        label="Publicación",
        widget=forms.Select(attrs={'class': 'form-control select2-post'}),
        empty_label="Todas las publicaciones"
    )

    created_date_range = CharFilter(
        label='Rango de Fechas',
        method='filter_by_date_range',
        widget=forms.TextInput(attrs={
            'class': 'form-control flatpickr-input',
            'placeholder': 'Seleccionar rango de fechas',
            'autocomplete': 'off'
        })
    )

    def filter_by_date_range(self, queryset, name, value):
        print(f"Filtrando comentarios por rango de fechas: {value}")
        if not value:
            return queryset

        try:
            # Divide el rango en inicio y fin
            start_date, end_date = value.split(' a ')
            start_date = parse_date(start_date.strip())
            end_date = parse_date(end_date.strip())
            if not start_date or not end_date:
                return queryset

            # Aplica el filtro usando created_at__date
            return queryset.filter(created_at__date__range=(start_date, end_date))
        except (ValueError, IndexError):
            return queryset

    class Meta:
        model = Comment
        fields = ['active', 'post', 'created_date_range']

# =====================================================================
# FILTROS DE MENSAJES DE CONTACTO
# =====================================================================


class ContactMessageFilter(django_filters.FilterSet):
    """
    Filtro para mensajes de contacto por tema, estado y fechas.
    """
    subject = ChoiceFilter(
        choices=ContactMessage.SUBJECT_CHOICES,
        label="Tema",
        widget=forms.Select(attrs={'class': 'form-control select2-subject'}),
        empty_label="Todos los temas"
    )
    
    is_read = ChoiceFilter(
        choices=(
            (True, 'Leídos'),
            (False, 'No leídos')
        ),
        label="Estado lectura",
        widget=forms.Select(attrs={'class': 'form-control select2-status'}),
        empty_label="Todos los estados"
    )
    
    is_answered = ChoiceFilter(
        choices=(
            (True, 'Respondidos'),
            (False, 'Pendientes')
        ),
        label="Estado respuesta",
        widget=forms.Select(attrs={'class': 'form-control select2-status'}),
        empty_label="Todos los estados"
    )

    created_date_range = CharFilter(
        label='Rango de Fechas',
        method='filter_by_date_range',
        widget=forms.TextInput(attrs={
            'class': 'form-control flatpickr-input',
            'placeholder': 'Seleccionar rango de fechas',
            'autocomplete': 'off'
        })
    )

    def filter_by_date_range(self, queryset, name, value):
        if not value:
            return queryset

        try:
            start_date, end_date = value.split(' a ')
            start_date = parse_date(start_date.strip())
            end_date = parse_date(end_date.strip())
            if not start_date or not end_date:
                return queryset

            return queryset.filter(created_at__date__range=(start_date, end_date))
        except (ValueError, IndexError):
            return queryset

    class Meta:
        model = ContactMessage
        fields = ['subject', 'is_read', 'is_answered', 'created_date_range']