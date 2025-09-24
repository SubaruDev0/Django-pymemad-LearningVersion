"""
Vistas para la gestión de Posts, Categorías, Tags y Comentarios
Este módulo contiene todas las vistas relacionadas con el contenido del blog
"""

# =====================================================================
# IMPORTACIONES ESTÁNDAR DE PYTHON
# =====================================================================
import json
import logging
import os
import tempfile
import traceback
from datetime import timezone

# =====================================================================
# IMPORTACIONES DE DJANGO
# =====================================================================
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import get_language
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView
)
from django_filters.views import FilterView

# =====================================================================
# IMPORTACIONES DE TERCEROS
# =====================================================================
import pandas as pd
from celery.result import AsyncResult

# =====================================================================
# IMPORTACIONES LOCALES
# =====================================================================
from apps.core.utils import encode_with_signer, decode_with_signer
from apps.landing.models import Post, Category, Tag, Comment
from apps.panel.filters import PostFilter, CategoryFilter, TagFilter, CommentFilter
from apps.panel.forms import PostForm, PostTagsForm, AiPostForm, PanelCommentForm
from apps.panel.tasks import (
    generate_post_ai_content_task,
    generate_post_translations_task,
    generate_all_metas_for_post
)
from apps.core.utils import save_file_to_s3, clear_panel_cache
from apps.panel.utils import clear_cache_for_post

# Configurar logger
logger = logging.getLogger(__name__)

# =====================================================================
# =====================================================================
#                     SECCIÓN 1: CRUD DE POSTS
# =====================================================================
# =====================================================================

@method_decorator(never_cache, name='dispatch')
class PostListView(LoginRequiredMixin, FilterView):
    """
    Muestra una lista de publicaciones del blog con soporte para filtrado
    y solicitudes AJAX para integración con DataTables.
    """
    model = Post
    template_name = 'posts/posts-list.html'
    context_object_name = 'posts'
    filterset_class = PostFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filterset = None
        self.object_list = None

    def get_queryset(self):
        """
        Optimiza el queryset para reducir consultas repetidas.
        """
        return Post.objects.select_related('author', 'category').prefetch_related(
            'tags',
            'translations'  # Precargar todas las traducciones
        ).annotate(
            total_comments=Count('comments')
        )

    def get_filterset_kwargs(self, filterset_class):
        """
        Permite personalizar los argumentos que se pasan al FilterSet.

        Parámetros:
            filterset_class: La clase de filtro que se está utilizando.

        Retorna:
            dict: Un diccionario kwargs que incluye los datos de filtrado correctamente procesados.
        """
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = self.request.GET.copy()
        kwargs['data'] = data
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la plantilla.
        """
        context = super().get_context_data(**kwargs)

        # Agregar categorías y autores para los filtros
        from apps.landing.models import Category
        from apps.accounts.models import User

        context['categories'] = Category.objects.all().order_by('name')
        context['authors'] = User.objects.filter(
            blog_posts__isnull=False,
            is_superuser=True
        ).distinct().order_by('username')

        context.update({
            'title_navbar': 'Administrar Publicaciones',
            'button_text': 'Nueva Publicación',
            'new_post_url': reverse('dashboard:post-create'),
            'title_page': 'Administrar Publicaciones',
        })
        return context

    def format_date(self, date):
        """
        Formatea una fecha para mostrar en DataTables.
        """
        return date.strftime('%Y-%m-%d %H:%M') if date else '-'

    def render_to_response(self, context, **response_kwargs):
        """
        Responde solicitudes AJAX con datos JSON para DataTables.
        """
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.filterset = self.get_filterset(self.filterset_class)
            if self.filterset.is_valid():
                queryset = self.filterset.qs
            else:
                queryset = self.get_queryset()

            draw = int(self.request.GET.get('draw', 1))
            start = int(self.request.GET.get('start', 0))
            length = int(self.request.GET.get('length', 10))
            search_value = self.request.GET.get('search[value]', '')

            # Columnas disponibles para ordenamiento (actualizado sin la columna de checkbox)
            column_list = [
                None,  # Columna 0: checkbox (no ordenable)
                'translations__title',  # Columna 1: título
                None,  # Columna 2: idiomas (no es un campo directo)
                'author__username',  # Columna 3: autor
                'publish',  # Columna 4: fecha de publicación
                'status',  # Columna 5: estado
                None  # Columna 6: acciones (no ordenable)
            ]

            # Ordenamiento
            order_column = int(self.request.GET.get('order[0][column]', '4'))  # Por defecto ordenar por fecha
            order_dir = self.request.GET.get('order[0][dir]', 'desc')

            # Verificar que la columna sea ordenable
            if order_column < len(column_list) and column_list[order_column]:
                order_field = column_list[order_column]
                if order_dir == 'desc':
                    order_field = '-' + order_field
            else:
                # Si la columna no es ordenable, usar orden por defecto
                order_field = '-publish'

            # Total de registros sin filtro
            records_total = queryset.count()

            # Filtro por búsqueda global
            if search_value:
                queryset = queryset.filter(
                    Q(translations__title__icontains=search_value) |
                    Q(author__username__icontains=search_value) |
                    Q(category__name__icontains=search_value) |
                    Q(tags__name__icontains=search_value)
                ).distinct()
                records_filtered = queryset.count()
            else:
                records_filtered = records_total

            # Aplicar ordenamiento y paginación
            queryset = queryset.order_by(order_field)[start:start + length]

            data = []
            for post in queryset:
                title = "Sin título en español"
                available_languages = []

                try:
                    # Sin alterar el idioma global
                    if post.has_translation('es'):
                        translation = post.get_translation('es')
                        title = translation.title or "Sin título en español"
                    else:
                        title = "Sin título en español"

                    # Idiomas disponibles
                    available_languages = [lang_code.upper() for lang_code, _ in settings.LANGUAGES if
                                           post.has_translation(lang_code)]

                except Exception as e:
                    print(f"[Error PostListView] {str(e)}")

                data.append({
                    "id": post.pk,
                    "title": title,
                    "languages": ", ".join(available_languages),
                    "author": post.author.username,
                    "publish": self.format_date(post.publish),
                    "status": post.get_status_display(),
                    "actions": mark_safe(
                        f'''
                        <div class="btn-group" role="group">
                            <a class="btn btn-sm btn-info text-white" 
                               href="{reverse('dashboard:post-update', args=[encode_with_signer(post.pk)])}"
                               title="Editar publicación">
                               <i class="ai-edit"></i>
                            </a>
                        </div>
                        '''
                    )
                })

            # Retornar datos en formato JSON
            return JsonResponse({
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": data
            })

        return super().render_to_response(context, **response_kwargs)


@method_decorator(never_cache, name='dispatch')
class PostCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para manejar la creación de publicaciones en el blog.
    """
    model = Post
    form_class = PostForm
    template_name = 'posts/post-create.html'

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional necesario para la plantilla.
        """
        context = super().get_context_data(**kwargs)

        # Configurar el formulario para que el status sea DRAFT por defecto
        if self.request.method == 'GET':
            form = context.get('form')
            if form:
                form.initial['status'] = 'DRAFT'

        context.update({
            'button_text': 'Crear Post',
            'title_navbar': 'Crear Nueva Publicación',
            'breadcrumb_item': 'Listar Publicaciones',
            'breadcrumb_item_url': reverse('dashboard:post-list'),
            'form_action': reverse('dashboard:post-create'),
            'current_language': get_language(),
        })
        return context

    def post(self, request, *args, **kwargs):
        """
        Override del método post para debuggear los datos recibidos.
        """
        print("\n=== DEBUG POST DATA ===")
        print("POST data keys:", request.POST.keys())

        # Imprimir contenido de los editores
        for lang in ['es', 'en', 'pt']:
            body_content = request.POST.get(f'body_{lang}', '')
            print(f"\nbody_{lang} content:")
            print(f"  - Length: {len(body_content)}")
            print(f"  - First 200 chars: {body_content[:200]}")
            print(f"  - Is empty: {not body_content.strip()}")

            title_content = request.POST.get(f'title_{lang}', '')
            print(f"\ntitle_{lang} content:")
            print(f"  - Content: {title_content}")
            print(f"  - Is empty: {not title_content.strip()}")

        print("\n=== END DEBUG ===\n")

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Maneja el caso en que el formulario es válido.
        """
        try:
            # Asignar el autor antes de guardar
            form.instance.author = self.request.user

            # Si no se especificó estado, usar DRAFT por defecto
            if not form.instance.status:
                form.instance.status = 'DRAFT'

            # Guardar el post
            post = form.save()

            # Log para debug
            logger.info(f"Post created successfully with ID: {post.pk}")
            logger.info(f"Post title (ES): {post.safe_translation_getter('title', language_code='es')}")

            # Preparar la URL de redirección (a la vista de edición)
            success_redirect = reverse('dashboard:post-update', kwargs={'pk': encode_with_signer(post.pk)})

            # Si la petición es AJAX, devolver JSON
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'La publicación fue creada exitosamente. Ahora puedes completar la información adicional.',
                    'redirect_url': success_redirect,
                    'post_id': encode_with_signer(post.pk)
                }, status=200)

            # Si no es AJAX, redirigir directamente
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(success_redirect)

        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")

            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Ocurrió un error al crear la publicación',
                    'errors': [str(e)]
                }, status=500)
            else:
                # Si no es AJAX, volver a mostrar el formulario con errores
                form.add_error(None, str(e))
                return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Maneja el caso en que el formulario es inválido.
        """
        logger.warning(f"Form validation failed: {form.errors}")

        # Si es una petición AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors_dict = {}
            for field, errors in form.errors.items():
                if field in form.fields:
                    errors_list = [str(e).strip("[]'") for e in errors]
                    errors_dict[field] = {
                        'field_name': form.fields[field].label or field,
                        'field_id': form.fields[field].widget.attrs.get('id', f'id_{field}'),
                        'messages': errors_list
                    }
                else:
                    # Errores no relacionados con campos específicos
                    errors_dict[field] = {
                        'field_name': 'General',
                        'field_id': '',
                        'messages': [str(e).strip("[]'") for e in errors]
                    }

            return JsonResponse({
                'success': False,
                'message': 'Por favor corrige los siguientes errores:',
                'errors': errors_dict
            }, status=400)

        # Si no es AJAX, usar el comportamiento por defecto
        return super().form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'posts/post-update.html'

    def get_object(self, queryset=None):
        """
        Decodifica el PK firmado y recupera el objeto correspondiente.
        """
        encoded_pk = self.kwargs.get('pk')
        if not encoded_pk:
            raise Http404('No se proporcionó un PK')

        try:
            decoded_object = decode_with_signer(encoded_pk)
        except Exception:
            raise Http404('Firma del PK inválida')

        if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
            raise Http404('Formato del PK inválido')

        decoded_pk = decoded_object['value_encode']

        if queryset is None:
            queryset = self.get_queryset()

        try:
            obj = queryset.get(pk=decoded_pk)
        except ObjectDoesNotExist:
            raise Http404('No se encontró la publicación con este PK')

        return obj

    def dispatch(self, request, *args, **kwargs):
        """
        Maneja excepciones y errores de obtención de objeto antes de procesar la solicitud.
        """
        try:
            self.object = self.get_object()
            # Guardar el estado original para comparar después
            self.original_status = self.object.status
            self.original_tags = list(self.object.tags.values_list('id', flat=True))
        except Http404 as e:
            return JsonResponse({
                'success': False,
                'message': str(e),
                'errors': [str(e)],
            }, status=404)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional para la plantilla.
        """
        context = super().get_context_data(**kwargs)

        # Obtener tags con sus IDs reales
        tags = self.object.tags.all()

        # Crear el JSON de tags con el ID real de la base de datos
        tags_data = []
        for tag in tags:
            tag_dict = {
                "id": str(tag.id),  # ID real de la base de datos
                "text": tag.name,  # Nombre para mostrar
            }
            tags_data.append(tag_dict)

        # Obtener título en español
        title_es = "Sin título en español"
        if self.object.has_translation('es'):
            translation_es = self.object.get_translation('es')
            title_es = translation_es.title or "Sin título en español"

        # Obtener todos los idiomas disponibles
        available_languages = [lang_code.upper() for lang_code, _ in settings.LANGUAGES
                               if self.object.has_translation(lang_code)]

        # Crear formulario de tags
        tags_form = PostTagsForm(instance=self.object)

        # Obtener comentarios asociados al post
        from apps.landing.models import Comment
        comments = self.object.comments.all().order_by('-created_at')

        # Preparar datos de comentarios para el template
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': encode_with_signer(comment.id),
                'name': comment.name,
                'email': comment.email,
                'body': comment.body,
                'active': comment.active,
                'created_at': comment.created_at,
            })

        context.update({
            'button_text': 'Guardar',
            'title_navbar': 'Actualizar Publicación',
            'breadcrumb_item': 'Listar Publicaciones',
            'breadcrumb_item_url': reverse('dashboard:post-list'),
            'form_action': reverse('dashboard:post-update', kwargs={'pk': encode_with_signer(self.object.pk)}),
            'tags_json': json.dumps(tags_data),
            'post_id': encode_with_signer(self.object.id),
            'form_ai': AiPostForm(),
            'tags_form': tags_form,  # Formulario de tags separado
            'title_es': title_es,
            'available_languages': ', '.join(available_languages),
            'post_status': self.object.status,
            'auto_generate_meta': self.object.auto_generate_meta,
            'comments': comments_data,
            'comments_count': comments.count(),
            'current_language': get_language(),  # Agregar idioma actual
        })
        return context

    def get_form_kwargs(self):
        """
        Pasa argumentos adicionales al formulario
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """
        Maneja el caso en que el formulario es válido.
        """
        try:
            # Detectar cambios importantes antes de guardar
            old_status = self.original_status
            new_status = form.cleaned_data.get('status')

            # Guardamos el post (sin tags)
            post = form.save()

            # Manejar los tags con el formulario separado
            tags_form = PostTagsForm(self.request.POST, instance=post)
            if tags_form.is_valid():
                # Guardar los tags
                post.tags.set(tags_form.cleaned_data.get('tags', []))

                # Verificar si los tags cambiaron
                new_tag_ids = [tag.id for tag in tags_form.cleaned_data.get('tags', [])]
                tags_changed = set(self.original_tags) != set(new_tag_ids)
            else:
                # Si hay errores en el formulario de tags, incluirlos en la respuesta
                return self.form_invalid_with_tags(form, tags_form)

            # Verificar cambios de contenido
            content_changed = self._check_content_changes(form) or tags_changed

            # Limpiar cualquier cache existente antes de iniciar
            clear_cache_for_post(post)

            # Variables para el mensaje y generación de metas
            generate_meta = False
            meta_message = None

            # Lógica para determinar si generar metas
            if post.auto_generate_meta:
                # Caso 1: Post cambió de DRAFT a PUBLISHED
                if old_status == 'DRAFT' and new_status == 'PUBLISHED':
                    generate_meta = True
                    meta_message = 'Post publicado. Generando meta descripciones SEO automáticamente...'
                    logger.info(f"Post {post.pk} cambió de DRAFT a PUBLISHED")

                # Caso 2: Post ya publicado con contenido actualizado significativamente
                elif new_status == 'PUBLISHED' and content_changed:
                    generate_meta = True
                    meta_message = 'Contenido actualizado. Regenerando meta descripciones SEO...'
                    logger.info(f"Post {post.pk} publicado con cambios significativos")

                # Caso 3: Regeneración manual solicitada
                elif form.cleaned_data.get('regenerate_meta', False):
                    generate_meta = True
                    meta_message = 'Regenerando meta descripciones SEO bajo demanda...'
                    logger.info(f"Regeneración manual solicitada para post {post.pk}")

            # Lanzar tarea de generación si es necesario
            task_id = None
            if generate_meta:
                task = generate_all_metas_for_post.apply_async(
                    args=[post.pk],
                    countdown=3  # 3 segundos de delay para asegurar que todo esté guardado
                )
                task_id = task.id
                logger.info(f"Tarea de generación de metas lanzada: {task_id}")

            # Mensaje principal
            main_message = 'La publicación fue actualizada exitosamente'

            # Construir mensaje completo
            if meta_message:
                full_message = f"{main_message}. {meta_message}"
            else:
                full_message = main_message

            success_redirect = reverse_lazy('dashboard:post-list')

            # Respuesta mejorada con información sobre generación de metas
            return JsonResponse({
                'success': True,
                'message': full_message,
                'redirect_url': str(success_redirect),
                'meta_generation': {
                    'initiated': generate_meta,
                    'task_id': task_id,
                    'message': meta_message
                } if generate_meta else None,
                'post_status': new_status,
                'status_changed': old_status != new_status,
                'cache_cleared': True,
                'tags_updated': tags_changed
            }, status=200)

        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': 'Error de validación',
                'errors': [str(e)]
            }, status=400)

        except Exception as e:
            logger.error(f"Error al actualizar la publicación: {str(e)}")
            import traceback
            traceback.print_exc()

            return JsonResponse({
                'success': False,
                'message': 'Ocurrió un error inesperado',
                'errors': ['Por favor, intenta nuevamente o contacta al soporte si el problema persiste']
            }, status=500)

    def form_invalid(self, form):
        """
        Maneja el caso en que el formulario es inválido.
        """
        errors_dict = {}
        for field, errors in form.errors.items():
            errors_list = [str(e).strip("[]'") for e in errors]
            errors_dict[field] = {
                'field_name': form.fields[field].label or field,
                'field_id': form.fields[field].widget.attrs.get('id', f'id_{field}'),
                'messages': errors_list
            }

        return JsonResponse({
            'success': False,
            'message': 'Por favor corrige los siguientes errores:',
            'errors': errors_dict
        }, status=400)

    def form_invalid_with_tags(self, form, tags_form):
        """
        Maneja errores cuando tanto el formulario principal como el de tags tienen errores
        """
        errors_dict = {}

        # Errores del formulario principal
        for field, errors in form.errors.items():
            errors_list = [str(e).strip("[]'") for e in errors]
            errors_dict[field] = {
                'field_name': form.fields[field].label or field,
                'field_id': form.fields[field].widget.attrs.get('id', f'id_{field}'),
                'messages': errors_list
            }

        # Errores del formulario de tags
        for field, errors in tags_form.errors.items():
            errors_list = [str(e).strip("[]'") for e in errors]
            errors_dict[f'tags_{field}'] = {
                'field_name': 'Etiquetas',
                'field_id': 'id_tags',
                'messages': errors_list
            }

        return JsonResponse({
            'success': False,
            'message': 'Por favor corrige los siguientes errores:',
            'errors': errors_dict
        }, status=400)

    def _check_content_changes(self, form):
        """
        Verifica si hubo cambios significativos en el contenido que justifiquen
        regenerar las meta descripciones.
        """
        # Campos traducidos que si cambian, justifican regenerar metas
        translated_fields = ['title_es', 'body_es', 'title_en', 'body_en', 'title_pt', 'body_pt']

        # Campos directos que también son significativos
        direct_fields = ['category', 'img_featured']

        # Verificar campos traducidos
        for field in translated_fields:
            if field in form.changed_data:
                logger.debug(f"Campo traducido cambió: {field}")
                return True

        # Verificar campos directos
        for field in direct_fields:
            if field in form.changed_data:
                logger.debug(f"Campo significativo cambió: {field}")
                return True

        # Los tags se verifican por separado en form_valid

        return False


# =====================================================================
# =====================================================================
#               SECCIÓN 2: ACCIONES MASIVAS DE POSTS
# =====================================================================
# =====================================================================

@method_decorator(never_cache, name='dispatch')
class PostBulkDeleteView(LoginRequiredMixin, View):
    """
    Vista para eliminación masiva de publicaciones seleccionadas.
    """

    def post(self, request, *args, **kwargs):
        try:
            # Obtener los IDs de publicaciones desde los datos POST
            post_ids = request.POST.getlist('post_ids[]')
            if not post_ids:
                # También intentar obtener como array normal
                post_ids = request.POST.getlist('post_ids')

            print(f"[BULK-DELETE] IDs recibidos del frontend: {post_ids}")

            if not post_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No se han proporcionado publicaciones para eliminar.'
                }, status=400)

            # Convertir los IDs a enteros
            decoded_ids = []
            for post_id in post_ids:
                try:
                    # Convertir a entero directamente
                    decoded_id = int(post_id)
                    decoded_ids.append(decoded_id)
                except (ValueError, TypeError) as e:
                    print(f"[BULK-DELETE] Error convirtiendo ID '{post_id}' a entero: {e}")
                    continue

            print(f"[BULK-DELETE] IDs convertidos a enteros: {decoded_ids}")

            if not decoded_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No se pudieron procesar los IDs proporcionados.'
                }, status=400)

            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                # Consultar las publicaciones válidas que pertenecen al usuario
                posts = Post.objects.filter(
                    pk__in=decoded_ids,
                ).select_related('category').prefetch_related('tags')

                print(f"[BULK-DELETE] Posts encontrados para eliminar: {list(posts.values_list('pk', flat=True))}")

                if not posts.exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'No se encontraron publicaciones válidas para eliminar.'
                    }, status=404)

                # Contar publicaciones antes de eliminar
                total_to_delete = posts.count()

                # Recopilar información para logging
                deleted_info = []
                for post in posts:
                    deleted_info.append({
                        'id': post.pk,
                        'title': post.title,
                        'status': post.get_status_display(),
                        'category': post.category.name if post.category else 'Sin categoría',
                        'tags_count': post.tags.count()
                    })

                # NOTA: delete() retorna (total_objetos_eliminados, diccionario_por_modelo)
                # El total incluye objetos relacionados eliminados en cascada (comments, likes, etc.)
                deleted_count, deletion_details = posts.delete()

                # Log detallado de la acción
                print(
                    f"\n[BULK-DELETE] Resumen de eliminación:\n"
                    f"- Usuario: {request.user.username}\n"
                    f"- Publicaciones eliminadas: {total_to_delete}\n"
                    f"- Total de objetos eliminados (con relaciones): {deleted_count}\n"
                    f"- Desglose por modelo: {deletion_details}\n"
                    f"- Detalles de publicaciones: {deleted_info}\n"
                )

                # Calcular publicaciones que no pudieron ser encontradas
                not_found = len(decoded_ids) - total_to_delete

                # Preparar mensaje de respuesta
                message = f'{total_to_delete} publicación(es) eliminada(s) correctamente'

                if not_found > 0:
                    message += f' ({not_found} no encontrada(s) o sin permisos)'

                return JsonResponse({
                    'success': True,
                    'message': message,
                    'deleted_count': total_to_delete,
                    'not_found': not_found,
                    'action': 'message'
                })

        except Exception as e:
            print(f"[ERROR] Error en PostBulkDeleteView: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar publicaciones: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class PostBulkStatusView(LoginRequiredMixin, View):
    """
    Vista para cambiar el estado de múltiples publicaciones.
    """

    def post(self, request, *args, **kwargs):
        try:
            # Obtener los IDs de publicaciones desde los datos POST
            post_ids = request.POST.getlist('post_ids[]')
            if not post_ids:
                # También intentar obtener como array normal
                post_ids = request.POST.getlist('post_ids')

            status = request.POST.get('status')

            if not post_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No se proporcionaron IDs de publicaciones'
                }, status=400)

            # Validar estado según el modelo
            if status not in ['PUBLISHED', 'DRAFT']:
                return JsonResponse({
                    'success': False,
                    'message': 'Estado inválido. Use PUBLISHED o DRAFT'
                }, status=400)

            # Convertir IDs a enteros
            decoded_ids = []
            for post_id in post_ids:
                try:
                    decoded_id = int(post_id)
                    decoded_ids.append(decoded_id)
                except (ValueError, TypeError) as e:
                    print(f"[BULK-STATUS] Error convirtiendo ID {post_id}: {e}")
                    continue

            if not decoded_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No se pudieron procesar los IDs proporcionados.'
                }, status=400)

            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                # Actualizar publicaciones sin filtro de autor
                updated_count = Post.objects.filter(
                    pk__in=decoded_ids
                ).update(
                    status=status,
                    updated_at=timezone.now()  # Actualizar timestamp
                )

                # Calcular cuántas no se actualizaron
                not_updated = len(decoded_ids) - updated_count

                # Log de la acción
                print(
                    f"[BULK-STATUS] Usuario {request.user.username} cambió el estado "
                    f"de {updated_count} publicaciones a '{status}'"
                )

                # Preparar mensaje
                status_display = 'publicadas' if status == 'PUBLISHED' else 'guardadas como borrador'
                message = f'{updated_count} publicación(es) {status_display}'

                if not_updated > 0:
                    message += f' ({not_updated} no encontrada(s))'

                return JsonResponse({
                    'success': True,
                    'message': message,
                    'updated_count': updated_count,
                    'not_updated': not_updated,
                    'action': 'message'
                })

        except Exception as e:
            print(f"[ERROR] Error en PostBulkStatusView: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar el estado: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class PostExportView(LoginRequiredMixin, View):
    """
    Vista para exportar publicaciones en formato Excel y subirlo a S3.
    """

    def post(self, request, *args, **kwargs):
        try:
            # Obtener los IDs de publicaciones desde los datos POST
            post_ids = request.POST.getlist('post_ids[]')
            if not post_ids:
                # También intentar obtener como array normal
                post_ids = request.POST.getlist('post_ids')

            format_type = request.POST.get('format', 'excel')
            include_content = request.POST.get('include_content', 'true') == 'true'

            if not post_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No se proporcionaron publicaciones para exportar'
                }, status=400)

            # Convertir IDs a enteros
            decoded_ids = []
            for post_id in post_ids:
                try:
                    decoded_id = int(post_id)
                    decoded_ids.append(decoded_id)
                except (ValueError, TypeError) as e:
                    print(f"[EXPORT] Error convirtiendo ID {post_id}: {e}")
                    continue

            if not decoded_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No se pudieron procesar los IDs proporcionados.'
                }, status=400)

            # Obtener las publicaciones sin filtro de autor
            posts = Post.objects.filter(
                pk__in=decoded_ids
            ).select_related('author', 'category').prefetch_related('tags')

            if not posts.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'No se encontraron publicaciones válidas para exportar'
                }, status=404)

            # Log de la acción
            print(
                f"[EXPORT] Usuario {request.user.username} exportando "
                f"{posts.count()} publicaciones en formato {format_type}"
            )

            # Preparar los datos para el DataFrame
            data = []
            for post in posts:
                # Obtener idiomas disponibles
                languages = []
                if hasattr(post, 'has_translation'):
                    from django.conf import settings
                    languages = [
                        lang_code.upper()
                        for lang_code, _ in settings.LANGUAGES
                        if post.has_translation(lang_code)
                    ]

                # Generar URL del post
                post_url = 'Sin URL'
                if post.publish and post.slug:
                    # Construir la URL completa del post
                    # Formato: https://dominio.com/es/noticias/YYYY/MM/DD/slug/
                    domain = request.get_host()
                    protocol = 'https' if request.is_secure() else 'http'
                    year = post.publish.year
                    month = post.publish.strftime('%m')
                    day = post.publish.strftime('%d')
                    # Usar idioma español por defecto
                    post_url = f"{protocol}://{domain}/es/news/{year}/{month}/{day}/{post.slug}/"

                row = {
                    'ID': post.pk,
                    'Título': post.title,
                    'URL': post_url,
                    'Autor': post.author.username if post.author else 'Sin autor',
                    'Categoría': post.category.name if post.category else 'Sin categoría',
                    'Idiomas': ', '.join(languages) if languages else 'ES',
                    'Estado': post.get_status_display(),
                    'Fecha de publicación': post.publish.strftime('%d-%m-%Y %H:%M') if post.publish else 'No publicado',
                    'Fecha de creación': post.created_at.strftime('%d-%m-%Y %H:%M') if post.created_at else '',
                    'Última actualización': post.updated_at.strftime('%d-%m-%Y %H:%M') if post.updated_at else '',
                }

                # Si necesitas agregar tags
                if post.tags.exists():
                    row['Tags'] = ', '.join([tag.name for tag in post.tags.all()])
                else:
                    row['Tags'] = 'Sin tags'

                data.append(row)

            # Crear DataFrame
            df = pd.DataFrame(data)

            # Crear archivo temporal para el Excel
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp:
                # Escribir Excel con formato
                with pd.ExcelWriter(temp.name, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Publicaciones', index=False)

                    # Obtener el workbook y worksheet para formato
                    workbook = writer.book
                    worksheet = writer.sheets['Publicaciones']

                    # Formato para encabezados
                    header_format = workbook.add_format({
                        'bold': True,
                        'text_wrap': True,
                        'valign': 'top',
                        'bg_color': '#4472C4',
                        'font_color': 'white',
                        'border': 1
                    })

                    # Aplicar formato a encabezados
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)

                    # Auto-ajustar ancho de columnas
                    for i, column in enumerate(df.columns):
                        column_len = df[column].astype(str).map(len).max()
                        column_len = max(column_len, len(column)) + 2
                        worksheet.set_column(i, i, min(column_len, 50))

                    # Congelar primera fila
                    worksheet.freeze_panes(1, 0)

                # Rebobinar el archivo temporal
                temp.seek(0)

                # Generar nombre de archivo
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                filename = f"publicaciones_export_{timestamp}"

                # Subir a S3
                excel_url = save_file_to_s3(
                    temp,
                    filename,
                    "exports/publicaciones",
                    file_extension="xlsx"
                )

                # Limpiar archivo temporal
                os.unlink(temp.name)

            # Verificar si la subida a S3 fue exitosa
            if not excel_url:
                return JsonResponse({
                    'success': False,
                    'message': 'Error al generar el archivo Excel en el servidor.'
                }, status=500)

            # Retornar el resultado como JSON
            return JsonResponse({
                'success': True,
                'file_path': excel_url,
                'filename': f"{filename}.xlsx",
                'total_posts': len(data),
                'message': f'Archivo generado exitosamente con {len(data)} publicaciones.',
                'download_url': excel_url  # URL directa para descargar
            })

        except Exception as e:
            print(f"[ERROR] Error en PostExportView: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error al exportar publicaciones: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class PostClearCacheView(LoginRequiredMixin, View):
    """
    Vista AJAX para limpiar el cache de un post específico
    """
    model = Post

    def decode_post_id(self, encoded_pk):
        """
        Decodifica el PK firmado y devuelve el ID real del post.
        """
        if not encoded_pk:
            raise Http404('No se proporcionó un post_id')

        try:
            decoded_object = decode_with_signer(encoded_pk)
        except Exception:
            raise Http404('Firma del post_id inválida')

        if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
            raise Http404('Formato del post_id inválido')

        return decoded_object['value_encode']

    def post(self, request):
        try:
            # Recibir el post_id codificado
            encoded_post_id = request.POST.get('post_id')

            # Decodificar el post_id
            try:
                post_id = self.decode_post_id(encoded_post_id)
            except Http404 as e:
                return JsonResponse({
                    "success": False,
                    "error": str(e)
                }, status=400)

            # Verificar que el post existe
            try:
                post = self.model.objects.get(pk=post_id)
            except self.model.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "La nota no ha sido encontrada"
                }, status=404)

            # Verificar permisos (opcional: solo el autor o admin puede limpiar cache)
            if not request.user.is_superuser and post.author != request.user:
                return JsonResponse({
                    'success': False,
                    'message': 'No tienes permisos para realizar esta acción'
                }, status=403)

            # Limpiar cache del post
            deleted_count = clear_cache_for_post(post, deep_clean=True)

            # Limpiar cache del panel también
            panel_deleted = clear_panel_cache()

            # Log de la acción
            logger.info(
                f"Cache limpiado por {request.user.username} para post {post_id}: "
                f"{deleted_count} claves del post, {panel_deleted} claves del panel"
            )

            return JsonResponse({
                'success': True,
                'message': f'Cache limpiado exitosamente. Se eliminaron {deleted_count + panel_deleted} entradas.',
                'details': {
                    'post_cache_cleared': deleted_count,
                    'panel_cache_cleared': panel_deleted
                }
            })

        except Exception as e:
            logger.error(f"Error al limpiar cache del post {post_id if 'post_id' in locals() else 'desconocido'}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error al limpiar el cache. Por favor, intenta nuevamente.'
            }, status=500)


# =====================================================================
# =====================================================================
#           SECCIÓN 3: INTELIGENCIA ARTIFICIAL PARA POSTS
# =====================================================================
# =====================================================================

@method_decorator(never_cache, name='dispatch')
class GetNewPostAI(View):
    model = Post

    def decode_post_id(self, encoded_pk):
        """
        Decodifica el PK firmado y devuelve el ID real del post.
        """
        if not encoded_pk:
            raise Http404('No se proporcionó un post_id')

        try:
            decoded_object = decode_with_signer(encoded_pk)
        except Exception:
            raise Http404('Firma del post_id inválida')

        if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
            raise Http404('Formato del post_id inválido')

        return decoded_object['value_encode']

    def post(self, request):
        try:
            # Recibir el post_id codificado
            encoded_post_id = request.POST.get('post_id')

            # Decodificar el post_id
            try:
                post_id = self.decode_post_id(encoded_post_id)
            except Http404 as e:
                return JsonResponse({
                    "success": False,
                    "error": str(e)
                }, status=400)

            # Obtener las instrucciones del usuario
            user_instructions = request.POST.get('ai_prompt', '').strip()

            # Verificar que el post existe
            try:
                post = self.model.objects.get(pk=post_id)
            except self.model.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "La nota no ha sido encontrada"
                }, status=404)

            # Validar que esté en borrador
            if post.status != "DRAFT":
                return JsonResponse({
                    "success": False,
                    "error": "La nota debe estar en estado borrador para generar contenido con IA"
                }, status=400)

            # Lanzar tarea en Celery
            task = generate_post_ai_content_task.apply_async(
                args=[post_id, request.user.id],
                kwargs={'user_instructions': user_instructions} if user_instructions else {},
                queue='long_tasks'
            )

            # URL de redirección
            redirect_url = reverse('dashboard:post-update', kwargs={'pk': encoded_post_id})

            return JsonResponse({
                "success": True,
                "message": "El proceso de generación de contenido ha comenzado. Recibirás un correo cuando finalice.",
                "redirect_url": redirect_url,
                "task_id": task.id,
                "post_id": encoded_post_id,
                "action": "message"  # Para mostrar solo el mensaje sin redirección automática
            })

        except Exception as err:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en GetNewPostAI: {str(err)}", exc_info=True)

            return JsonResponse({
                "success": False,
                "error": f'Error iniciando generación de contenido: {str(err)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class GeneratePostTranslationsAI(View):
    model = Post

    def decode_post_id(self, encoded_pk):
        """
        Decodifica el PK firmado y devuelve el ID real del post.
        """
        if not encoded_pk:
            raise Http404('No se proporcionó un post_id')

        try:
            decoded_object = decode_with_signer(encoded_pk)
        except Exception:
            raise Http404('Firma del post_id inválida')

        if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
            raise Http404('Formato del post_id inválido')

        return decoded_object['value_encode']

    def post(self, request):
        try:
            # Obtener el post_id codificado del request
            encoded_post_id = request.POST.get('post_id')

            # Decodificar el post_id
            try:
                post_id = self.decode_post_id(encoded_post_id)
            except Http404 as e:
                return JsonResponse({
                    "success": False,
                    "error": str(e)
                }, status=400)

            # Verificar que el post existe
            try:
                post = self.model.objects.get(pk=post_id)
            except self.model.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "El post especificado no existe"
                }, status=404)

            # Verificar permisos (opcional)
            if hasattr(self, 'check_permissions'):
                if not self.check_permissions(request, post):
                    return JsonResponse({
                        "success": False,
                        "error": "No tienes permisos para realizar esta acción"
                    }, status=403)

            # Limpiar cualquier cache existente antes de iniciar
            clear_cache_for_post(post)

            # Lanzar tarea en segundo plano
            task = generate_post_translations_task.apply_async(
                args=[post_id, request.user.id],
                queue='long_tasks'
            )

            # URL de redirección opcional
            redirect_url = reverse('dashboard:post-update', kwargs={'pk': encoded_post_id})

            return JsonResponse({
                "success": True,
                "message": "El proceso de traducción ha comenzado. Te notificaremos cuando esté listo.",
                "redirect_url": redirect_url,
                "task_id": task.id,
                "post_id": encoded_post_id,  # Devolver el ID codificado
                "action": "message"  # Para mostrar solo el mensaje sin redirección automática
            })

        except Exception as err:
            logger.error(f"Error en GeneratePostTranslationsAI: {str(err)}", exc_info=True)

            return JsonResponse({
                "success": False,
                "error": f'Error inesperado: {str(err)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class PostRegenerateMetaView(LoginRequiredMixin, View):
    """
    Vista AJAX para regenerar meta descripciones del post
    """

    def post(self, request, pk):
        try:
            # Obtener el post
            post = get_object_or_404(Post, pk=pk)

            # Verificar permisos
            if not request.user.is_superuser and post.author != request.user:
                return JsonResponse({
                    'success': False,
                    'message': 'No tienes permisos para realizar esta acción'
                }, status=403)

            # Verificar si el post tiene auto_generate_meta activado
            if not post.auto_generate_meta:
                return JsonResponse({
                    'success': False,
                    'message': 'La generación automática de meta descripciones está desactivada para este post'
                }, status=400)

            # Lanzar tarea de generación
            task = generate_all_metas_for_post.apply_async(
                args=[post.pk],
                countdown=2  # 2 segundos de delay
            )

            logger.info(f"Tarea de regeneración de metas lanzada para post {pk}: {task.id}")

            return JsonResponse({
                'success': True,
                'message': 'Regeneración de meta descripciones iniciada',
                'task_id': task.id
            })

        except Exception as e:
            logger.error(f"Error al regenerar metas para post {pk}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error al iniciar la regeneración. Por favor, intenta nuevamente.'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class CheckAITaskStatus(View):
    def get(self, request):
        task_id = request.GET.get('task_id')

        if not task_id:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó task_id'
            }, status=400)

        try:
            task = AsyncResult(task_id)

            if task.state == 'PENDING':
                response = {
                    'status': 'pending',
                    'message': 'Tarea en espera...'
                }
            elif task.state == 'STARTED':
                response = {
                    'status': 'started',
                    'message': 'Generando contenido...'
                }
            elif task.state == 'SUCCESS':
                response = {
                    'status': 'completed',
                    'result': task.result
                }
            elif task.state == 'FAILURE':
                response = {
                    'status': 'failed',
                    'error': str(task.info)
                }
            else:
                response = {
                    'status': task.state.lower(),
                    'message': f'Estado: {task.state}'
                }

            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error verificando tarea: {str(e)}'
            }, status=500)


# =====================================================================
# =====================================================================
#              SECCIÓN 4: API Y BÚSQUEDA DE POSTS
# =====================================================================
# =====================================================================

class DashboardStatsAPIView(LoginRequiredMixin, TemplateView):
    """
    API endpoint para actualizar las estadísticas del dashboard.
    """

    def get(self, request, *args, **kwargs):
        """
        Devuelve las estadísticas actualizadas en formato JSON.
        """
        # Importar modelos necesarios

        # Calcular estadísticas
        total_posts = Post.objects.filter(status='PUBLISHED').count()

        try:
            from apps.landing.models import Contact
            total_contacts = Contact.objects.count()
        except:
            total_contacts = 0

        try:
            from apps.landing.models import Comment
            total_comments = Comment.objects.filter(active=True).count()
        except:
            total_comments = 0

        total_views = 0  # Placeholder

        return JsonResponse({
            'total_posts': total_posts,
            'total_contacts': total_contacts,
            'total_comments': total_comments,
            'total_views': total_views,
            'published_posts': Post.objects.filter(status='PUBLISHED').count(),
            'draft_posts': Post.objects.filter(status='DRAFT').count(),
            'scheduled_posts': Post.objects.filter(
                status='PUBLISHED',
                publish__gt=timezone.now()
            ).count()
        })


@method_decorator(never_cache, name='dispatch')
class PostSearchView(LoginRequiredMixin, View):
    """
    Vista para búsqueda de posts en Select2
    """

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        page = int(request.GET.get('page', 1))
        per_page = 30

        # Buscar posts
        posts = Post.objects.all()
        if query:
            posts = posts.filter(
                Q(translations__title__icontains=query) |
                Q(translations__slug__icontains=query)
            ).distinct()

        # Paginación
        total_count = posts.count()
        start = (page - 1) * per_page
        end = start + per_page
        posts = posts[start:end]

        # Preparar resultados
        results = []
        for post in posts:
            # Obtener título en español
            title = "Sin título"
            try:
                if post.has_translation('es'):
                    translation = post.get_translation('es')
                    title = translation.title or "Sin título"
            except:
                pass

            results.append({
                'id': post.pk,
                'text': title
            })

        return JsonResponse({
            'items': results,
            'total_count': total_count
        })


# =====================================================================
# =====================================================================
#               SECCIÓN 5: GESTIÓN DE COMENTARIOS
# =====================================================================
# =====================================================================

@method_decorator(never_cache, name='dispatch')
class CommentListView(LoginRequiredMixin, ListView):
    """
    Vista principal para listar todos los comentarios del sistema
    """
    model = Comment
    template_name = 'posts/comments-list.html'
    context_object_name = 'comments'
    paginate_by = 20

    def get_queryset(self):
        """
        Optimiza el queryset para reducir consultas.
        """
        return Comment.objects.select_related('post').order_by('-created_at')

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto.
        """
        context = super().get_context_data(**kwargs)
        context.update({
            'title_navbar': 'Administrar Comentarios',
            'title_page': 'Listado de Comentarios',
            'total_comments': Comment.objects.count(),
            'active_comments': Comment.objects.filter(active=True).count(),
            'pending_comments': Comment.objects.filter(active=False).count(),
        })
        return context


@method_decorator(never_cache, name='dispatch')
class CommentListView(LoginRequiredMixin, FilterView):
    """
    Vista para listar y filtrar comentarios con análisis gráfico
    """
    model = Comment
    template_name = 'posts/comments-list.html'
    context_object_name = 'comments'
    filterset_class = CommentFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filterset = None
        self.object_list = None

    def get_queryset(self):
        """
        Optimiza el queryset para reducir consultas.
        """
        return Comment.objects.select_related('post').order_by('-created_at')

    def get_filterset_kwargs(self, filterset_class):
        """
        Permite personalizar los argumentos que se pasan al FilterSet.
        """
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = self.request.GET.copy()
        kwargs['data'] = data
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la plantilla.
        """
        context = super().get_context_data(**kwargs)

        # Obtener el queryset filtrado
        filtered_qs = self.get_filterset(self.filterset_class).qs

        # Estadísticas generales
        context['total_comments'] = filtered_qs.count()
        context['active_comments'] = filtered_qs.filter(active=True).count()
        context['pending_comments'] = filtered_qs.filter(active=False).count()

        # Análisis por estado
        status_stats = {
            'Publicados': filtered_qs.filter(active=True).count(),
            'Pendientes': filtered_qs.filter(active=False).count()
        }

        # Top posts con más comentarios
        top_posts = filtered_qs.values('post__id').annotate(
            comment_count=Count('id')
        ).order_by('-comment_count')[:5]

        # Obtener los posts completos con sus títulos
        top_posts_with_titles = []
        for item in top_posts:
            try:
                post = Post.objects.get(id=item['post__id'])
                if post.has_translation('es'):
                    translation = post.get_translation('es')
                    title = translation.title or "Sin título"
                else:
                    title = "Sin título"
                top_posts_with_titles.append({
                    'title': title,
                    'count': item['comment_count']
                })
            except Post.DoesNotExist:
                continue

        # Preparar datos para gráficos
        context['chart_data'] = {
            'status': {
                'labels': list(status_stats.keys()),
                'data': list(status_stats.values())
            },
            'timeline': self.get_timeline_data(filtered_qs),
            'top_posts': {
                'labels': [p['title'][:30] + '...' if len(p['title']) > 30 else p['title']
                           for p in top_posts_with_titles],
                'data': [p['count'] for p in top_posts_with_titles]
            }
        }

        context.update({
            'title_navbar': 'Administrar Comentarios',
            'title_page': 'Listado de Comentarios',
            'status_stats': status_stats,
            'top_posts': top_posts_with_titles,
            'current_language': self.request.LANGUAGE_CODE,  # Agregar idioma actual
        })

        return context

    def get_timeline_data(self, queryset):
        """
        Genera datos para el gráfico de línea temporal
        """
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from datetime import timedelta

        # Obtener últimos 30 días
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        # Agrupar por día
        daily_counts = queryset.filter(
            created_at__date__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        # Preparar datos para el gráfico
        dates = []
        counts = []

        # Llenar todos los días incluso sin datos
        current_date = start_date
        daily_dict = {item['date']: item['count'] for item in daily_counts}

        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            counts.append(daily_dict.get(current_date, 0))
            current_date += timedelta(days=1)

        return {
            'labels': dates,
            'data': counts
        }

    def format_date(self, date):
        """
        Formatea una fecha para mostrar en DataTables.
        """
        return date.strftime('%Y-%m-%d %H:%M') if date else '-'

    def render_to_response(self, context, **response_kwargs):
        """
        Responde solicitudes AJAX con datos JSON para DataTables.
        """
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.filterset = self.get_filterset(self.filterset_class)
            if self.filterset.is_valid():
                queryset = self.filterset.qs
            else:
                queryset = self.get_queryset()

            draw = int(self.request.GET.get('draw', 1))
            start = int(self.request.GET.get('start', 0))
            length = int(self.request.GET.get('length', 10))
            search_value = self.request.GET.get('search[value]', '')

            # Columnas disponibles para ordenamiento
            column_list = [
                None,  # Columna 0: checkbox (no ordenable)
                'name',  # Columna 1: autor
                'email',  # Columna 2: email
                'post',  # Columna 3: post
                'body',  # Columna 4: comentario
                'active',  # Columna 5: estado
                'created_at',  # Columna 6: fecha
                None  # Columna 7: acciones (no ordenable)
            ]

            # Ordenamiento
            order_column = int(self.request.GET.get('order[0][column]', 6))  # Por defecto ordenar por fecha
            order_dir = self.request.GET.get('order[0][dir]', 'desc')

            # Verificar que la columna sea ordenable
            if order_column < len(column_list) and column_list[order_column]:
                order_field = column_list[order_column]
                if order_dir == 'desc':
                    order_field = '-' + order_field
            else:
                order_field = '-created_at'

            # Total de registros sin filtro
            records_total = queryset.count()

            # Filtro por búsqueda global
            if search_value:
                queryset = queryset.filter(
                    Q(name__icontains=search_value) |
                    Q(email__icontains=search_value) |
                    Q(body__icontains=search_value) |
                    Q(post__translations__title__icontains=search_value)
                ).distinct()
                records_filtered = queryset.count()
            else:
                records_filtered = records_total

            # Aplicar ordenamiento y paginación
            queryset = queryset.order_by(order_field)[start:start + length]

            data = []
            for comment in queryset:
                # Obtener título del post
                post_title = "Sin título"
                try:
                    if comment.post.has_translation('es'):
                        translation = comment.post.get_translation('es')
                        post_title = translation.title or "Sin título"
                except:
                    pass

                # Truncar comentario si es muy largo
                comment_preview = comment.body[:100] + '...' if len(comment.body) > 100 else comment.body

                # Preparar valores para evitar f-string anidados
                badge_class = "success" if comment.active else "warning"
                badge_text = "Publicado" if comment.active else "Pendiente"

                # Construir botones condicionales
                approve_button = "" if comment.active else f'''
                            <button class="btn btn-sm btn-success approve-comment" 
                                data-id="{comment.pk}"
                                title="Aprobar comentario">
                                <i class="ai-check"></i>
                            </button>
                            '''

                reject_button = "" if not comment.active else f'''
                            <button class="btn btn-sm btn-warning reject-comment" 
                                data-id="{comment.pk}"
                                title="Rechazar comentario">
                                <i class="ai-x"></i>
                            </button>
                            '''

                data.append({
                    "id": comment.pk,
                    "name": comment.name,
                    "email": comment.email,
                    "post": post_title[:50] + '...' if len(post_title) > 50 else post_title,
                    "body": comment_preview,
                    "active": mark_safe(
                        f'<span class="badge bg-{badge_class}">'
                        f'{badge_text}</span>'
                    ),
                    "created_at": self.format_date(comment.created_at),
                    "actions": mark_safe(
                        f'''
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-info text-white view-comment" 
                                data-id="{comment.pk}"
                                data-name="{comment.name}"
                                data-email="{comment.email}"
                                data-body="{comment.body}"
                                data-post="{post_title}"
                                data-active="{comment.active}"
                                data-date="{self.format_date(comment.created_at)}"
                                title="Ver detalles">
                                <i class="ai-show"></i>
                            </button>
                            {approve_button}
                            {reject_button}
                            <button class="btn btn-sm btn-info text-white edit-comment" 
                                data-id="{comment.pk}"
                                title="Editar comentario">
                                <i class="ai-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-comment" 
                                data-id="{comment.pk}"
                                title="Eliminar comentario">
                                <i class="ai-trash"></i>
                            </button>
                        </div>
                        '''
                    )
                })

            # Retornar datos en formato JSON
            return JsonResponse({
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": data
            })

        return super().render_to_response(context, **response_kwargs)

@method_decorator(never_cache, name='dispatch')
class CommentDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar un comentario específico
    """
    model = Comment
    success_url = reverse_lazy('dashboard:comment-list')
    
    def delete(self, request, *args, **kwargs):
        """
        Elimina el comentario
        """
        self.object = self.get_object()
        comment_id = self.object.pk
        self.object.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Comentario #{comment_id} eliminado correctamente'
            })
        
        return HttpResponseRedirect(self.success_url)


@method_decorator(never_cache, name='dispatch')
class CommentManageView(LoginRequiredMixin, View):
    """
    Vista para gestionar comentarios desde el panel de posts
    Maneja GET, POST, PUT y DELETE para operaciones CRUD
    """

    def get(self, request, *args, **kwargs):
        """
        Obtiene los datos de un comentario específico para editar.
        """
        encoded_pk = kwargs.get('pk')
        if not encoded_pk:
            return JsonResponse({
                'success': False,
                'message': 'No se proporcionó un ID de comentario'
            }, status=400)

        try:
            # Decodificar el PK
            decoded_object = decode_with_signer(encoded_pk)
            if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
                raise ValueError('Formato del PK inválido')

            comment_pk = decoded_object['value_encode']

            # Obtener el comentario
            from apps.landing.models import Comment
            comment = Comment.objects.get(pk=comment_pk)

            # Preparar los datos del comentario
            comment_data = {
                'id': encoded_pk,
                'name': comment.name,
                'email': comment.email,
                'body': comment.body,
                'active': comment.active,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'post_title': comment.post.safe_translation_getter('title', any_language=True)
            }

            return JsonResponse({
                'success': True,
                'comment': comment_data
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al obtener el comentario: {str(e)}'
            }, status=404)

    def post(self, request, *args, **kwargs):
        """
        Actualiza un comentario existente.
        """
        encoded_pk = kwargs.get('pk')
        if not encoded_pk:
            return JsonResponse({
                'success': False,
                'message': 'No se proporcionó un ID de comentario'
            }, status=400)

        try:
            # Decodificar el PK
            decoded_object = decode_with_signer(encoded_pk)
            if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
                raise ValueError('Formato del PK inválido')

            comment_pk = decoded_object['value_encode']

            # Obtener el comentario
            from apps.landing.models import Comment
            comment = Comment.objects.get(pk=comment_pk)

            # Procesar el campo active correctamente
            post_data = request.POST.copy()
            if 'active' in post_data:
                # Convertir 'on' a True, cadena vacía a False
                post_data['active'] = post_data['active'] == 'on'

            # Log para depuración
            logger.info(f"Updating comment {comment_pk}")
            logger.info(f"POST data after processing: {post_data}")

            # Crear formulario con los datos procesados
            form = PanelCommentForm(post_data, instance=comment)

            if form.is_valid():
                comment = form.save()
                logger.info(f"Comment {comment_pk} updated successfully")

                return JsonResponse({
                    'success': True,
                    'message': 'Comentario actualizado correctamente',
                    'comment': {
                        'id': encoded_pk,
                        'name': comment.name,
                        'email': comment.email,
                        'body': comment.body,
                        'active': comment.active,
                        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                })
            else:
                logger.error(f"Form validation errors: {form.errors}")
                return JsonResponse({
                    'success': False,
                    'message': 'Error al validar el formulario',
                    'errors': form.errors.as_json()
                }, status=400)

        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comentario no encontrado'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating comment: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar el comentario: {str(e)}'
            }, status=500)

    def put(self, request, *args, **kwargs):
        """
        Actualiza el estado de un comentario (aprobar/rechazar).
        """
        encoded_pk = kwargs.get('pk')
        if not encoded_pk:
            return JsonResponse({
                'success': False,
                'message': 'No se proporcionó un ID de comentario'
            }, status=400)

        try:
            # Decodificar el PK
            decoded_object = decode_with_signer(encoded_pk)
            if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
                raise ValueError('Formato del PK inválido')

            comment_pk = decoded_object['value_encode']

            # Obtener el comentario
            from apps.landing.models import Comment
            comment = Comment.objects.get(pk=comment_pk)

            # Parsear el body de la request
            import json
            data = json.loads(request.body)
            action = data.get('action')

            if action == 'approve':
                comment.active = True
                comment.save()
                message = 'Comentario aprobado y publicado'
            elif action == 'reject':
                comment.active = False
                comment.save()
                message = 'Comentario rechazado'
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Acción no válida'
                }, status=400)

            return JsonResponse({
                'success': True,
                'message': message,
                'active': comment.active
            })

        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comentario no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar el estado: {str(e)}'
            }, status=500)

    def delete(self, request, *args, **kwargs):
        """
        Elimina un comentario.
        """
        encoded_pk = kwargs.get('pk')
        if not encoded_pk:
            return JsonResponse({
                'success': False,
                'message': 'No se proporcionó un ID de comentario'
            }, status=400)

        try:
            # Decodificar el PK
            decoded_object = decode_with_signer(encoded_pk)
            if not isinstance(decoded_object, dict) or 'value_encode' not in decoded_object:
                raise ValueError('Formato del PK inválido')

            comment_pk = decoded_object['value_encode']

            # Obtener y eliminar el comentario
            from apps.landing.models import Comment
            comment = Comment.objects.get(pk=comment_pk)
            comment.delete()

            return JsonResponse({
                'success': True,
                'message': 'Comentario eliminado correctamente'
            })

        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comentario no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar el comentario: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class CommentUpdateView(LoginRequiredMixin, View):
    """
    Vista para actualizar un comentario (aprobar/rechazar/editar)
    """

    def get(self, request, *args, **kwargs):
        try:
            comment_id = kwargs.get('pk')
            comment = Comment.objects.get(pk=comment_id)

            # Obtener título del post
            post_title = "Sin título"
            try:
                if comment.post.has_translation('es'):
                    translation = comment.post.get_translation('es')
                    post_title = translation.title or "Sin título"
            except:
                pass

            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.pk,
                    'name': comment.name,
                    'email': comment.email,
                    'body': comment.body,
                    'active': comment.active,
                    'post_title': post_title,
                    'created_at': self.format_date(comment.created_at)
                }
            })
        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comentario no encontrado'
            }, status=404)

    def post(self, request, *args, **kwargs):
        try:
            comment_id = kwargs.get('pk')
            comment = Comment.objects.get(pk=comment_id)

            # Obtener la acción a realizar
            action = request.POST.get('action')

            if action == 'approve':
                comment.active = True
                comment.save()
                message = 'Comentario aprobado correctamente'
            elif action == 'reject':
                comment.active = False
                comment.save()
                message = 'Comentario rechazado correctamente'
            elif action == 'edit':
                # Actualizar los campos del comentario
                comment.name = request.POST.get('name', comment.name)
                comment.email = request.POST.get('email', comment.email)
                comment.body = request.POST.get('body', comment.body)
                comment.active = request.POST.get('active', '').lower() == 'true'
                comment.save()
                message = 'Comentario actualizado correctamente'
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Acción no válida'
                }, status=400)

            return JsonResponse({
                'success': True,
                'message': message
            })

        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comentario no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar comentario: {str(e)}'
            }, status=500)

    def format_date(self, date):
        """
        Formatea una fecha para mostrar.
        """
        return date.strftime('%Y-%m-%d %H:%M') if date else '-'


# =====================================================================
# =====================================================================
#                 SECCIÓN 6: GESTIÓN DE CATEGORÍAS
# =====================================================================
# =====================================================================

@method_decorator(never_cache, name='dispatch')
class CategoryListView(LoginRequiredMixin, FilterView):
    """
    Vista para listar y filtrar categorías
    """
    model = Category
    template_name = 'posts/categories-list.html'
    context_object_name = 'categories'
    filterset_class = CategoryFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filterset = None
        self.object_list = None

    def get_queryset(self):
        """
        Optimiza el queryset para reducir consultas.
        """
        return Category.objects.annotate(
            post_count=Count('posts')
        ).order_by('name')

    def get_filterset_kwargs(self, filterset_class):
        """
        Permite personalizar los argumentos que se pasan al FilterSet.
        """
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = self.request.GET.copy()
        kwargs['data'] = data
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la plantilla.
        """
        context = super().get_context_data(**kwargs)

        # Obtener el queryset filtrado
        filtered_qs = self.get_filterset(self.filterset_class).qs

        # Estadísticas generales
        context['total_categories'] = filtered_qs.count()
        context['categories_with_posts'] = filtered_qs.filter(posts__isnull=False).distinct().count()
        context['empty_categories'] = filtered_qs.filter(posts__isnull=True).count()

        context.update({
            'title_navbar': 'Administrar Categorías',
            'title_page': 'Listado de Categorías',
            'current_language': self.request.LANGUAGE_CODE,  # Agregar idioma actual
        })

        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Responde solicitudes AJAX con datos JSON para DataTables.
        """
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.filterset = self.get_filterset(self.filterset_class)
            if self.filterset.is_valid():
                queryset = self.filterset.qs
            else:
                queryset = self.get_queryset()

            draw = int(self.request.GET.get('draw', 1))
            start = int(self.request.GET.get('start', 0))
            length = int(self.request.GET.get('length', 10))
            search_value = self.request.GET.get('search[value]', '')

            # Columnas disponibles para ordenamiento
            column_list = [
                None,  # Columna 0: checkbox (no ordenable)
                'name',  # Columna 1: nombre
                'slug',  # Columna 2: slug
                None,  # Columna 3: posts (no directamente ordenable, pero podríamos usar anotaciones)
                'created_at',  # Columna 4: fecha creación
                None  # Columna 5: acciones (no ordenable)
            ]

            # Ordenamiento
            order_column = int(self.request.GET.get('order[0][column]', 1))  # Por defecto ordenar por nombre
            order_dir = self.request.GET.get('order[0][dir]', 'asc')

            # Verificar que la columna sea ordenable
            if order_column < len(column_list) and column_list[order_column]:
                order_field = column_list[order_column]
                if order_dir == 'desc':
                    order_field = '-' + order_field
            else:
                order_field = 'name'

            # Total de registros sin filtro
            records_total = queryset.count()

            # Filtro por búsqueda global
            if search_value:
                queryset = queryset.filter(
                    Q(name__icontains=search_value) |
                    Q(slug__icontains=search_value)
                ).distinct()
                records_filtered = queryset.count()
            else:
                records_filtered = records_total

            # Aplicar ordenamiento y paginación
            queryset = queryset.order_by(order_field)[start:start + length]

            data = []
            for category in queryset:
                data.append({
                    "id": category.pk,
                    "name": category.name,
                    "slug": category.slug,
                    "post_count": category.post_count if hasattr(category, 'post_count') else category.posts.count(),
                    "created_at": category.created_at.strftime('%Y-%m-%d %H:%M') if category.created_at else '-',
                    "actions": mark_safe(
                        f'''
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-info text-white edit-category" 
                                data-id="{category.pk}"
                                data-name="{category.name}"
                                data-slug="{category.slug}"
                                title="Editar categoría">
                                <i class="ai-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-category" 
                                data-id="{category.pk}"
                                data-name="{category.name}"
                                title="Eliminar categoría">
                                <i class="ai-trash"></i>
                            </button>
                        </div>
                        '''
                    )
                })

            # Retornar datos en formato JSON
            return JsonResponse({
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": data
            })

        return super().render_to_response(context, **response_kwargs)


@method_decorator(never_cache, name='dispatch')
class CategoryCreateView(LoginRequiredMixin, View):
    """
    Vista para crear una nueva categoría
    """

    def post(self, request):
        """
        Crea una nueva categoría
        """
        try:
            # Obtener los datos del POST
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()

            # Validar datos requeridos
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'El nombre es requerido'
                }, status=400)

            # Si no se proporciona slug, generarlo desde el nombre
            if not slug:
                slug = slugify(name)

            # Verificar que el slug no esté duplicado
            if Category.objects.filter(slug=slug).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Ya existe una categoría con el slug "{slug}"'
                }, status=400)

            # Crear la categoría
            category = Category.objects.create(
                name=name,
                slug=slug
            )

            return JsonResponse({
                'success': True,
                'message': 'Categoría creada exitosamente',
                'category_id': category.pk
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al crear la categoría: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class CategoryUpdateView(LoginRequiredMixin, View):
    """
    Vista para actualizar una categoría específica
    """

    def get(self, request, pk):
        """
        Obtiene los datos de una categoría para edición
        """
        try:
            category = Category.objects.get(pk=pk)

            return JsonResponse({
                'success': True,
                'category': {
                    'id': category.pk,
                    'name': category.name,
                    'slug': category.slug,
                }
            })

        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Categoría no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar la categoría: {str(e)}'
            }, status=500)

    def post(self, request, pk):
        """
        Actualiza una categoría
        """
        try:
            category = Category.objects.get(pk=pk)

            # Obtener los datos del POST
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()

            # Validar datos requeridos
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'El nombre es requerido'
                }, status=400)

            # Si no se proporciona slug, generarlo desde el nombre
            if not slug:
                slug = slugify(name)

            # Verificar que el slug no esté duplicado (excepto para la misma categoría)
            if Category.objects.exclude(pk=pk).filter(slug=slug).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Ya existe una categoría con el slug "{slug}"'
                }, status=400)

            # Actualizar la categoría
            category.name = name
            category.slug = slug
            category.save()

            return JsonResponse({
                'success': True,
                'message': 'Categoría actualizada exitosamente'
            })

        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Categoría no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar la categoría: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class CategoryDeleteView(LoginRequiredMixin, View):
    """
    Vista para eliminar una categoría específica
    """

    def delete(self, request, pk):
        """
        Elimina una categoría
        """
        try:
            category = Category.objects.get(pk=pk)

            # Verificar si la categoría tiene posts asociados
            post_count = category.posts.count()
            if post_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'No se puede eliminar la categoría porque tiene {post_count} posts asociados. Primero debe reasignar o eliminar estos posts.'
                }, status=400)

            # Guardar el nombre antes de eliminar
            category_name = category.name

            # Eliminar la categoría
            category.delete()

            return JsonResponse({
                'success': True,
                'message': f'Categoría "{category_name}" eliminada exitosamente'
            })

        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Categoría no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar la categoría: {str(e)}'
            }, status=500)


# =====================================================================
# =====================================================================
#                  SECCIÓN 7: GESTIÓN DE TAGS
# =====================================================================
# =====================================================================

@method_decorator(never_cache, name='dispatch')
class TagListView(LoginRequiredMixin, FilterView):
    """
    Vista para listar y filtrar tags
    """
    model = Tag
    template_name = 'posts/tags-list.html'
    context_object_name = 'tags'
    filterset_class = TagFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filterset = None
        self.object_list = None

    def get_queryset(self):
        """
        Optimiza el queryset para reducir consultas.
        """
        return Tag.objects.annotate(
            post_count=Count('posts')
        ).order_by('name')

    def get_filterset_kwargs(self, filterset_class):
        """
        Permite personalizar los argumentos que se pasan al FilterSet.
        """
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = self.request.GET.copy()
        kwargs['data'] = data
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto de la plantilla.
        """
        context = super().get_context_data(**kwargs)

        # Obtener el queryset filtrado
        filtered_qs = self.get_filterset(self.filterset_class).qs

        # Estadísticas generales
        context['total_tags'] = filtered_qs.count()
        context['tags_with_posts'] = filtered_qs.filter(posts__isnull=False).distinct().count()
        context['empty_tags'] = filtered_qs.filter(posts__isnull=True).count()

        context.update({
            'title_navbar': 'Administrar Etiquetas',
            'title_page': 'Listado de Etiquetas',
            'current_language': self.request.LANGUAGE_CODE,  # Agregar idioma actual
        })

        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Responde solicitudes AJAX con datos JSON para DataTables.
        """
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.filterset = self.get_filterset(self.filterset_class)
            if self.filterset.is_valid():
                queryset = self.filterset.qs
            else:
                queryset = self.get_queryset()

            draw = int(self.request.GET.get('draw', 1))
            start = int(self.request.GET.get('start', 0))
            length = int(self.request.GET.get('length', 10))
            search_value = self.request.GET.get('search[value]', '')

            # Columnas disponibles para ordenamiento
            column_list = [
                None,  # Columna 0: checkbox (no ordenable)
                'name',  # Columna 1: nombre
                'slug',  # Columna 2: slug
                None,  # Columna 3: posts (no directamente ordenable)
                'created_at',  # Columna 4: fecha creación
                None  # Columna 5: acciones (no ordenable)
            ]

            # Ordenamiento
            order_column = int(self.request.GET.get('order[0][column]', 1))  # Por defecto ordenar por nombre
            order_dir = self.request.GET.get('order[0][dir]', 'asc')

            # Verificar que la columna sea ordenable
            if order_column < len(column_list) and column_list[order_column]:
                order_field = column_list[order_column]
                if order_dir == 'desc':
                    order_field = '-' + order_field
            else:
                order_field = 'name'

            # Total de registros sin filtro
            records_total = queryset.count()

            # Filtro por búsqueda global
            if search_value:
                queryset = queryset.filter(
                    Q(name__icontains=search_value) |
                    Q(slug__icontains=search_value)
                ).distinct()
                records_filtered = queryset.count()
            else:
                records_filtered = records_total

            # Aplicar ordenamiento y paginación
            queryset = queryset.order_by(order_field)[start:start + length]

            data = []
            for tag in queryset:
                data.append({
                    "id": tag.pk,
                    "name": tag.name,
                    "slug": tag.slug,
                    "post_count": tag.post_count if hasattr(tag, 'post_count') else tag.posts.count(),
                    "created_at": tag.created_at.strftime('%Y-%m-%d %H:%M') if tag.created_at else '-',
                    "actions": mark_safe(
                        f'''
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-info text-white edit-tag" 
                                data-id="{tag.pk}"
                                data-name="{tag.name}"
                                data-slug="{tag.slug}"
                                title="Editar etiqueta">
                                <i class="ai-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-tag" 
                                data-id="{tag.pk}"
                                data-name="{tag.name}"
                                title="Eliminar etiqueta">
                                <i class="ai-trash"></i>
                            </button>
                        </div>
                        '''
                    )
                })

            # Retornar datos en formato JSON
            return JsonResponse({
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": data
            })

        return super().render_to_response(context, **response_kwargs)


@method_decorator(never_cache, name='dispatch')
class TagCreateView(LoginRequiredMixin, View):
    """
    Vista para crear una nueva etiqueta
    """

    def post(self, request):
        """
        Crea una nueva etiqueta
        """
        try:
            # Obtener los datos del POST
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()

            # Validar datos requeridos
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'El nombre es requerido'
                }, status=400)

            # Si no se proporciona slug, generarlo desde el nombre
            if not slug:
                slug = slugify(name)

            # Verificar que el slug no esté duplicado
            if Tag.objects.filter(slug=slug).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Ya existe una etiqueta con el slug "{slug}"'
                }, status=400)

            # Crear la etiqueta
            tag = Tag.objects.create(
                name=name,
                slug=slug
            )

            return JsonResponse({
                'success': True,
                'message': 'Etiqueta creada exitosamente',
                'tag_id': tag.pk
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al crear la etiqueta: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class TagUpdateView(LoginRequiredMixin, View):
    """
    Vista para actualizar una etiqueta específica
    """

    def get(self, request, pk):
        """
        Obtiene los datos de una etiqueta para edición
        """
        try:
            tag = Tag.objects.get(pk=pk)

            return JsonResponse({
                'success': True,
                'tag': {
                    'id': tag.pk,
                    'name': tag.name,
                    'slug': tag.slug,
                }
            })

        except Tag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Etiqueta no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar la etiqueta: {str(e)}'
            }, status=500)

    def post(self, request, pk):
        """
        Actualiza una etiqueta
        """
        try:
            tag = Tag.objects.get(pk=pk)

            # Obtener los datos del POST
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()

            # Validar datos requeridos
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'El nombre es requerido'
                }, status=400)

            # Si no se proporciona slug, generarlo desde el nombre
            if not slug:
                slug = slugify(name)

            # Verificar que el slug no esté duplicado (excepto para la misma etiqueta)
            if Tag.objects.exclude(pk=pk).filter(slug=slug).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Ya existe una etiqueta con el slug "{slug}"'
                }, status=400)

            # Actualizar la etiqueta
            tag.name = name
            tag.slug = slug
            tag.save()

            return JsonResponse({
                'success': True,
                'message': 'Etiqueta actualizada exitosamente'
            })

        except Tag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Etiqueta no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar la etiqueta: {str(e)}'
            }, status=500)


@method_decorator(never_cache, name='dispatch')
class TagDeleteView(LoginRequiredMixin, View):
    """
    Vista para eliminar una etiqueta específica
    """

    def delete(self, request, pk):
        """
        Elimina una etiqueta
        """
        try:
            tag = Tag.objects.get(pk=pk)

            # Verificar si la etiqueta tiene posts asociados
            post_count = tag.posts.count()
            if post_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'No se puede eliminar la etiqueta porque tiene {post_count} posts asociados. Primero debe quitar esta etiqueta de los posts.'
                }, status=400)

            # Guardar el nombre antes de eliminar
            tag_name = tag.name

            # Eliminar la etiqueta
            tag.delete()

            return JsonResponse({
                'success': True,
                'message': f'Etiqueta "{tag_name}" eliminada exitosamente'
            })

        except Tag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Etiqueta no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar la etiqueta: {str(e)}'
            }, status=500)
