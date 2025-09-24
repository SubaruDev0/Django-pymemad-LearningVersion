"""
Formularios específicos para el panel de administración
Este módulo contiene todos los formularios utilizados en el panel
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from parler.forms import TranslatableModelForm

from apps.landing.models import Post, Category, Tag, Comment

class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, *args, **kwargs):
        # Usamos un formato que sea compatible con 'datetime-local'
        super(CustomDateTimeInput, self).__init__(format='%Y-%m-%dT%H:%M', *args, **kwargs)


# =====================================================================
# =====================================================================
#                    SECCIÓN 1: FORMULARIOS DE POSTS
# =====================================================================
# =====================================================================

class PostForm(TranslatableModelForm):
    title_es = forms.CharField(label="Título (Español)", required=False, widget=forms.TextInput(attrs={
        'class': 'form-control my-3',
        'id': 'title_es'
    }))
    body_es = forms.CharField(label="Contenido (Español)", required=False, widget=forms.HiddenInput())

    title_en = forms.CharField(label="Título (Inglés)", required=False, widget=forms.TextInput(attrs={
        'class': 'form-control my-3',
        'id': 'title_en'
    }))
    body_en = forms.CharField(label="Contenido (Inglés)", required=False, widget=forms.HiddenInput())

    title_pt = forms.CharField(label="Título (Portugués)", required=False, widget=forms.TextInput(attrs={
        'class': 'form-control my-3',
        'id': 'title_pt'
    }))
    body_pt = forms.CharField(label="Contenido (Portugués)", required=False, widget=forms.HiddenInput())

    class Meta:
        model = Post
        fields = (
            'category',
            'img_featured',
            'publish',
            'status',
            # 'tags', # REMOVIDO - se maneja en formulario separado
        )

        labels = {
            'category': 'Categoría',
            'img_featured': 'Foto Destacada',
            'status': 'Estado',
            'publish': 'Fecha Publicación',
        }

        widgets = {
            'img_featured': forms.FileInput(attrs={
                'class': 'form-control-file my-3',
                'id': 'photo',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control my-3',
                'id': 'status',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control my-3',
                'id': 'category',
            }),
            'publish': CustomDateTimeInput(attrs={
                'class': 'form-control my-3',
                'id': 'published_at',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            for lang in ['es', 'en', 'pt']:
                self.instance.set_current_language(lang)
                self.fields[f'title_{lang}'].initial = self.instance.title
                self.fields[f'body_{lang}'].initial = self.instance.body

        self.initial_status = self.instance.status if self.instance.pk else None

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')

        self.should_send_whatsapp = (
                self.initial_status != 'PUBLISHED' and new_status == 'PUBLISHED'
        )

        return cleaned_data

    def clean_title_es(self):
        return self._validate_unique_title('es', 'title_es')

    def clean_title_en(self):
        return self._validate_unique_title('en', 'title_en')

    def clean_title_pt(self):
        return self._validate_unique_title('pt', 'title_pt')

    def _validate_unique_title(self, lang, field_name):
        title = self.cleaned_data.get(field_name)
        if not title:
            return title
        existing = Post.published.translated(lang, title__iexact=title).exclude(pk=self.instance.pk).first()
        if existing:
            raise ValidationError(f'El título ya existe en {lang.upper()}.')
        return title

    def save(self, commit=True):
        """
        Sobreescribe el método save para manejar correctamente las traducciones y slugs.
        NO maneja tags - eso se hace en el formulario separado
        """
        instance = super().save(commit=False)

        if not instance.pk and hasattr(self, 'request') and self.request:
            instance.author = self.request.user

        if commit:
            instance.save()

        # Guardar todas las traducciones
        for lang in ['es', 'en', 'pt']:
            title = self.cleaned_data.get(f'title_{lang}', '')
            body = self.cleaned_data.get(f'body_{lang}', '')

            if title or body:
                instance.set_current_language(lang)

                if title:
                    instance.title = title
                    instance.slug = instance._generate_unique_slug(lang, title)

                if body:
                    instance.body = body

                instance.save_translations()

        # Volver a establecer el idioma a español
        instance.set_current_language('es')

        # Guardar la instancia final
        if commit:
            instance.save()

        return instance


class PostTagsForm(forms.ModelForm):
    """
    Formulario separado para manejar los tags del post
    """

    class Meta:
        model = Post
        fields = ['tags']
        widgets = {
            'tags': forms.SelectMultiple(
                attrs={
                    'class': 'form-select form-select-lg',
                    'id': 'id_tags',
                    'multiple': 'multiple'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar el queryset para incluir todos los tags disponibles
        self.fields['tags'].queryset = Tag.objects.all()

        # Si hay una instancia, establecer los valores iniciales
        if self.instance and self.instance.pk:
            self.fields['tags'].initial = self.instance.tags.all()

    def clean_tags(self):
        """
        Procesa los tags, permitiendo crear nuevos si es necesario
        """
        tag_data = self.cleaned_data.get('tags', [])

        if not tag_data:
            return []

        processed_tags = []

        # tag_data puede contener objetos Tag o IDs/nombres
        for tag_item in tag_data:
            if isinstance(tag_item, Tag):
                processed_tags.append(tag_item)
            elif isinstance(tag_item, (int, str)):
                try:
                    # Intentar buscar por ID
                    if str(tag_item).isdigit():
                        tag = Tag.objects.get(pk=int(tag_item))
                        processed_tags.append(tag)
                    else:
                        # Buscar o crear por nombre
                        tag_name = str(tag_item).strip()
                        tag, created = Tag.objects.get_or_create(
                            name=tag_name,
                            defaults={'slug': slugify(tag_name)}
                        )
                        processed_tags.append(tag)
                except Tag.DoesNotExist:
                    # Crear nuevo tag
                    tag_name = str(tag_item).strip()
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name,
                        defaults={'slug': slugify(tag_name)}
                    )
                    processed_tags.append(tag)

        return processed_tags


class AiPostForm(forms.Form):
    ai_new_post = forms.CharField(label="Propuesta Ai",widget=forms.Textarea(attrs={'class': 'form-control my-2', 'id': 'id_ai_post',}))


class BulkActionForm(forms.Form):
    """
    Formulario para acciones masivas en posts
    """
    
    ACTIONS = [
        ('', '-- Seleccionar Acción --'),
        ('delete', 'Eliminar seleccionados'),
        ('publish', 'Publicar seleccionados'),
        ('draft', 'Cambiar a borrador'),
        ('export', 'Exportar a Excel'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTIONS,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'bulk-action-select'
        })
    )
    
    post_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )


# =====================================================================
# =====================================================================
#                 SECCIÓN 2: FORMULARIOS DE CATEGORÍAS
# =====================================================================
# =====================================================================

class CategoryForm(forms.ModelForm):
    """
    Formulario para crear y editar categorías
    """
    
    class Meta:
        model = Category
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría',
                'required': True
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'url-amigable',
                'help_text': 'Se genera automáticamente del nombre si se deja vacío'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer el slug opcional (se genera automáticamente si está vacío)
        self.fields['slug'].required = False
    
    def clean_slug(self):
        """
        Valida y genera el slug automáticamente
        """
        slug = self.cleaned_data.get('slug')
        name = self.cleaned_data.get('name')
        
        if not slug and name:
            slug = slugify(name)
        
        # Verificar unicidad
        if slug:
            qs = Category.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe una categoría con este slug.')
        
        return slug


# =====================================================================
# =====================================================================
#                  SECCIÓN 3: FORMULARIOS DE ETIQUETAS
# =====================================================================
# =====================================================================

class TagForm(forms.ModelForm):
    """
    Formulario para crear y editar etiquetas
    """
    
    class Meta:
        model = Tag
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la etiqueta',
                'required': True
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'url-amigable',
                'help_text': 'Se genera automáticamente del nombre si se deja vacío'
            })
        }
    
    def clean_slug(self):
        """
        Valida y genera el slug automáticamente
        """
        slug = self.cleaned_data.get('slug')
        name = self.cleaned_data.get('name')
        
        if not slug and name:
            slug = slugify(name)
        
        # Verificar unicidad
        if slug:
            qs = Tag.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe una etiqueta con este slug.')
        
        return slug
    
    def clean_name(self):
        """
        Valida el nombre de la etiqueta
        """
        name = self.cleaned_data.get('name')
        
        if name:
            # Normalizar: eliminar espacios extras y capitalizar
            name = ' '.join(name.split())
            
            # Verificar unicidad del nombre (case-insensitive)
            qs = Tag.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe una etiqueta con este nombre.')
        
        return name


class BulkTagForm(forms.Form):
    """
    Formulario para crear múltiples etiquetas a la vez
    """
    
    tags = forms.CharField(
        label='Etiquetas',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Ingresa una etiqueta por línea'
        }),
        help_text='Cada línea se convertirá en una nueva etiqueta'
    )
    
    def clean_tags(self):
        """
        Procesa y valida las etiquetas ingresadas
        """
        tags_text = self.cleaned_data.get('tags')
        tags_list = []
        
        if tags_text:
            # Separar por líneas y limpiar
            lines = tags_text.strip().split('\n')
            for line in lines:
                tag = line.strip()
                if tag and tag not in tags_list:
                    tags_list.append(tag)
        
        if not tags_list:
            raise ValidationError('Debe ingresar al menos una etiqueta.')
        
        return tags_list


# =====================================================================
# =====================================================================
#                SECCIÓN 4: FORMULARIOS DE COMENTARIOS
# =====================================================================
# =====================================================================

class PanelCommentForm(forms.ModelForm):
    """
    Formulario para editar comentarios en el panel de administración
    """
    class Meta:
        model = Comment
        fields = ['name', 'email', 'body', 'active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del comentarista'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Correo electrónico'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Contenido del comentario'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'Nombre',
            'email': 'Correo Electrónico',
            'body': 'Comentario',
            'active': 'Publicado'
        }


class CommentReplyForm(forms.Form):
    """
    Formulario para responder a comentarios
    """
    
    reply = forms.CharField(
        label='Respuesta',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Escribe tu respuesta aquí...'
        }),
        required=True
    )
    
    send_email = forms.BooleanField(
        label='Notificar por email',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Enviar respuesta por correo al autor del comentario'
    )


class BulkCommentActionForm(forms.Form):
    """
    Formulario para acciones masivas en comentarios
    """
    
    ACTIONS = [
        ('', '-- Seleccionar Acción --'),
        ('approve', 'Aprobar seleccionados'),
        ('reject', 'Rechazar seleccionados'),
        ('delete', 'Eliminar seleccionados'),
        ('mark_spam', 'Marcar como spam'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTIONS,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    comment_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
