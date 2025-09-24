# Estructura Modular de Filtros - Guía de Organización

## Estructura Actual vs Estructura Recomendada

### Estructura Actual (Problemática)
```
apps/
├── landing/
│   └── filters.py  # TODOS los filtros mezclados
└── panel/
    └── views.py    # Importa filtros de landing
```

### Estructura Recomendada (Modular)
```
apps/
├── landing/
│   └── filters.py  # Solo filtros públicos del landing
├── panel/
│   └── filters.py  # Filtros específicos del panel admin
├── accounts/
│   └── filters.py  # Filtros de usuarios si necesario
└── core/
    └── filters/
        ├── __init__.py
        └── base.py     # Clases base reutilizables
```

## Ventajas de la Separación por Aplicativo

### 1. **Separación de Responsabilidades**
- Cada app mantiene sus propios filtros
- El panel no depende de la app landing
- Mejor encapsulación del código

### 2. **Mantenibilidad**
- Archivos más pequeños y manejables
- Más fácil encontrar filtros específicos
- Menos conflictos en control de versiones

### 3. **Reutilización**
- Filtros base compartidos en `core/filters/base.py`
- Herencia clara entre filtros
- Menos duplicación de código

### 4. **Rendimiento**
- Importaciones más eficientes
- Solo se cargan los filtros necesarios
- Menor uso de memoria

## Contenido del Nuevo `apps/panel/filters.py`

### Filtros Incluidos:
1. **PostFilter** - Filtrado completo de posts con:
   - Búsqueda por título
   - Filtro por categoría
   - Filtro por estado (DRAFT/PUBLISHED)
   - Filtro por autor
   - Rango de fechas
   - Filtro por tags
   - Búsqueda general

2. **CategoryFilter** - Filtrado de categorías con:
   - Búsqueda por nombre y slug
   - Filtro por categorías con/sin posts
   - Ordenamiento personalizable

3. **TagFilter** - Filtrado de etiquetas con:
   - Búsqueda por nombre y slug
   - Filtro por tags con/sin posts
   - Filtro por número mínimo de posts
   - Ordenamiento

4. **CommentFilter** - Filtrado de comentarios con:
   - Búsqueda en contenido
   - Filtro por nombre y email
   - Filtro por estado (aprobado/pendiente)
   - Filtro por post asociado
   - Rango de fechas

## Migración Paso a Paso

### 1. Actualizar las importaciones en `post_views.py`:

```python
# Antes (importando desde landing)
from apps.landing.filters import PostFilter, CategoryFilter, TagFilter

# Después (importando desde panel)
from apps.panel.filters import PostFilter, CategoryFilter, TagFilter
```

### 2. Crear filtros base reutilizables (opcional):

```python
# apps/core/filters/base.py
import django_filters
from django import forms

class BaseModelFilter(django_filters.FilterSet):
    """Filtro base con configuración común"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar clases Bootstrap a todos los widgets
        for field in self.form.fields.values():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'


class SearchableFilter(BaseModelFilter):
    """Filtro con búsqueda general incorporada"""
    
    search = django_filters.CharFilter(
        method='search_filter',
        label='Buscar',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar...'
        })
    )
    
    def search_filter(self, queryset, name, value):
        # Sobrescribir en clases hijas
        return queryset
```

### 3. Limpiar `apps/landing/filters.py`:

Remover los filtros que son específicos del panel y dejar solo los que se usan en el frontend público:

```python
# apps/landing/filters.py
# Solo mantener filtros usados en vistas públicas
class PublicPostFilter(django_filters.FilterSet):
    """Filtro simplificado para posts públicos"""
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        empty_label='Todas las categorías'
    )
    
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        empty_label='Todas las etiquetas'
    )
    
    class Meta:
        model = Post
        fields = ['category', 'tag']
```

## Uso en las Vistas

### Ejemplo de uso en vista del panel:

```python
# apps/panel/post_views.py
from apps.panel.filters import PostFilter

class PostListView(LoginRequiredMixin, FilterView):
    model = Post
    template_name = 'panel/posts/list.html'
    filterset_class = PostFilter  # Usando el filtro del panel
    paginate_by = 20
    
    def get_queryset(self):
        return Post.objects.select_related('author', 'category').prefetch_related('tags')
```

### Ejemplo en template:

```html
<!-- templates/panel/posts/list.html -->
<form method="get" class="mb-4">
    <div class="row">
        <div class="col-md-4">
            {{ filter.form.title }}
        </div>
        <div class="col-md-3">
            {{ filter.form.category }}
        </div>
        <div class="col-md-3">
            {{ filter.form.status }}
        </div>
        <div class="col-md-2">
            <button type="submit" class="btn btn-primary">
                <i class="ai-search"></i> Filtrar
            </button>
        </div>
    </div>
</form>
```

## Personalización Avanzada

### Agregar filtros dinámicos según permisos:

```python
class PostFilter(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        # Obtener el request del kwargs
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Mostrar filtro de autor solo para superusuarios
        if request and not request.user.is_superuser:
            self.filters.pop('author', None)
```

### Filtros con autocomplete usando Select2:

```python
class PostFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-multiple',
            'data-placeholder': 'Seleccionar etiquetas...',
            'multiple': 'multiple'
        })
    )
```

## Mejores Prácticas

1. **Nombres descriptivos**: Usar nombres que indiquen claramente qué filtra
2. **Widgets apropiados**: Usar DateInput para fechas, Select para opciones limitadas
3. **Placeholders útiles**: Agregar placeholders descriptivos en los inputs
4. **Valores por defecto**: Considerar valores por defecto para mejorar UX
5. **Validación**: Agregar validación personalizada cuando sea necesario
6. **Performance**: Usar select_related y prefetch_related en querysets
7. **Documentación**: Documentar filtros complejos con docstrings

## Testing

### Ejemplo de test para filtros:

```python
# apps/panel/tests/test_filters.py
from django.test import TestCase
from apps.panel.filters import PostFilter
from apps.landing.models import Post, Category

class PostFilterTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.post = Post.objects.create(
            title='Test Post',
            category=self.category,
            status='PUBLISHED'
        )
    
    def test_filter_by_category(self):
        filter_data = {'category': self.category.id}
        f = PostFilter(filter_data, queryset=Post.objects.all())
        self.assertIn(self.post, f.qs)
    
    def test_filter_by_status(self):
        filter_data = {'status': 'PUBLISHED'}
        f = PostFilter(filter_data, queryset=Post.objects.all())
        self.assertIn(self.post, f.qs)
```

## Conclusión

La separación de filtros por aplicación mejora significativamente la organización del código, facilita el mantenimiento y permite una mejor escalabilidad del proyecto. Esta estructura modular es especialmente beneficiosa en proyectos grandes con múltiples desarrolladores.