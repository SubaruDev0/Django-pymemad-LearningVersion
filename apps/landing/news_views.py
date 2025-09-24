import hashlib

import pytz
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, Count
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _, get_language
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView

from apps.landing.forms import CommentForm
from apps.landing.models import Post, Category, Tag, Comment


@method_decorator(cache_page(settings.CACHE_TIMES.get('news_list', 1800)), name='dispatch')
@method_decorator(vary_on_headers('Accept-Language', 'X-Requested-With'), name='dispatch')
class PostListView(ListView):
    """Vista de lista de posts con cache y queries optimizadas"""

    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 6
    template_name = 'news.html'

    def get_cache_key(self):
        """Genera una cache key única basada en los filtros"""
        current_lang = get_language()
        tag_slug = self.kwargs.get('tag_slug', '')
        category_slug = self.request.GET.get('category', '')
        search_query = self.request.GET.get('search', '').strip()
        page = self.request.GET.get('page', '1')

        # Crear una key única basada en todos los parámetros
        key_parts = [
            'post_list',
            current_lang,
            tag_slug,
            category_slug,
            hashlib.md5(search_query.encode()).hexdigest()[:8] if search_query else 'no_search',
            f'page_{page}'
        ]

        return '_'.join(filter(None, key_parts))

    def get_queryset(self):
        """Filtra publicaciones con cache de queries complejas"""
        # Inicializar atributos aquí porque necesitamos self.request
        self.tags = None
        self.category = None
        self.search_query = self.request.GET.get('search', '').strip()
        self.invalid_filter = False

        # Intentar obtener de cache primero
        cache_key = f'queryset_{self.get_cache_key()}'
        cached_ids = cache.get(cache_key)

        if cached_ids is not None:
            # Reconstruir el queryset desde los IDs cacheados con optimizaciones
            return Post.objects.filter(
                id__in=cached_ids
            ).select_related(
                'author',
                'category'
            ).prefetch_related(
                'translations',
                'tags',
                'comments'  # Si necesitas contar comentarios
            ).order_by('-publish')

        # Si no está en cache, hacer la query normal
        queryset = super().get_queryset()
        current_lang = get_language()

        # Optimizar con select_related y prefetch_related
        queryset = queryset.select_related(
            'author',  # Para evitar queries adicionales al acceder al autor
            'category'  # Para evitar queries adicionales al acceder a la categoría
        ).prefetch_related(
            'translations',  # Para todas las traducciones
            'tags',  # Para los tags
            'comments'  # Si necesitas mostrar cantidad de comentarios
        )

        # Filtro base por idioma
        queryset = queryset.translated(current_lang)

        tag_slug = self.kwargs.get('tag_slug')
        category_slug = self.request.GET.get('category')

        try:
            if category_slug:
                self.category = Category.objects.get(slug=category_slug)
                queryset = queryset.filter(category=self.category)

            if tag_slug:
                self.tags = Tag.objects.get(slug=tag_slug)
                queryset = queryset.filter(tags=self.tags)

            if self.search_query:
                queryset = queryset.filter(
                    Q(translations__language_code=current_lang) & (
                            Q(translations__title__icontains=self.search_query) |
                            Q(translations__body__icontains=self.search_query)
                    )
                )

            queryset = queryset.distinct()

            # Cachear los IDs del resultado
            post_ids = list(queryset.values_list('id', flat=True))
            cache.set(cache_key, post_ids, 60 * 30)  # Cache por 30 minutos

            return queryset

        except Category.DoesNotExist:
            self.invalid_filter = True
            self.category = None
            return Post.published.none()

        except Tag.DoesNotExist:
            self.invalid_filter = True
            self.tags = None
            return Post.published.none()

    def get_context_data(self, **kwargs):
        """Agrega información adicional al contexto con cache"""
        context = super().get_context_data(**kwargs)
        current_lang = get_language()

        # Cache de categorías y tags
        cache_key_categories = f'all_categories_{current_lang}'
        cache_key_tags = f'all_tags_{current_lang}'

        categories = cache.get(cache_key_categories)
        if categories is None:
            categories = list(Category.objects.all())
            cache.set(cache_key_categories, categories, 60 * 60 * 2)  # 2 horas

        tags = cache.get(cache_key_tags)
        if tags is None:
            tags = list(Tag.objects.all())
            cache.set(cache_key_tags, tags, 60 * 60 * 2)  # 2 horas

        # Construir URL canónica
        scheme = self.request.scheme
        host = self.request.get_host()
        path = self.request.path
        base_url = f"{scheme}://{host}{path}"

        query_params = {}
        category = self.request.GET.get('category')
        if category:
            query_params['category'] = category

        page = self.request.GET.get('page')
        if page and page != '1':
            query_params['page'] = page

        search = self.request.GET.get('search')
        if search:
            query_params['search'] = search

        canonical_url = base_url
        if query_params:
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            canonical_url = f"{base_url}?{query_string}"

        context.update({
            'tag': self.tags,
            'category': self.category,
            'search_query': self.search_query,
            'title': _('Noticias PYMEMAD'),
            'subtitle': _('Mantente informado sobre las actividades, proyectos y logros de nuestra asociación.'),
            'categories': categories,
            'tags': tags,
            'canonical_url': canonical_url,
            'invalid_filter': getattr(self, 'invalid_filter', False),
        })

        return context


# Cache más largo para artículos (4 horas)
@method_decorator(cache_page(settings.CACHE_TIMES.get('news_detail', 14400)), name='dispatch')
@method_decorator(vary_on_headers('Accept-Language'), name='dispatch')
class PostDetailView(DetailView):
    """Vista de detalle con cache agresivo y optimizaciones"""

    model = Post
    template_name = 'news-single.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        """Obtiene el objeto Post con cache"""
        current_lang = get_language()
        slug = self.kwargs['post']
        year = self.kwargs['year']
        month = self.kwargs['month']
        day = self.kwargs['day']

        # Cache key para este post específico
        cache_key = f'post_detail_{year}_{month}_{day}_{slug}_{current_lang}'
        cached_result = cache.get(cache_key)

        if cached_result:
            if isinstance(cached_result, str) and cached_result.startswith('redirect:'):
                # Es una redirección cacheada
                return HttpResponseRedirect(cached_result.replace('redirect:', ''))
            else:
                # Es el post cacheado
                return cached_result

        # Importar datetime y timezone de Chile
        from datetime import datetime
        chile_tz = pytz.timezone('America/Santiago')
        
        # Crear fecha en zona horaria de Chile
        try:
            # Crear datetime naive
            target_date = datetime(year, month, day)
            # Localizarla en zona horaria de Chile
            target_date_chile = chile_tz.localize(target_date)
            # Convertir a UTC para la búsqueda en la BD
            target_date_utc = target_date_chile.astimezone(pytz.UTC)
            
            # Crear rango de fechas para todo el día en Chile
            start_of_day = target_date_chile
            end_of_day = target_date_chile.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Convertir a UTC para la búsqueda
            start_utc = start_of_day.astimezone(pytz.UTC)
            end_utc = end_of_day.astimezone(pytz.UTC)
        except (ValueError, pytz.exceptions.AmbiguousTimeError):
            raise Http404("Fecha inválida")

        # Query optimizada con prefetch usando rango de fechas
        possible_posts = Post.published.filter(
            publish__gte=start_utc,
            publish__lte=end_utc
        ).prefetch_related(
            'translations',
            'tags',
            'comments'
        ).select_related('author', 'category')

        if not possible_posts.exists():
            raise Http404

        # Buscar el post correcto
        post = None
        for p in possible_posts:
            for lang in p.get_available_languages():
                trans = p.get_translation(lang)
                if trans.slug == slug:
                    post = p
                    break
            if post:
                break

        if not post:
            raise Http404

        # Verificar redirección
        if current_lang in post.get_available_languages():
            current_trans = post.get_translation(current_lang)
            correct_slug = current_trans.slug

            if slug != correct_slug:
                localized_publish = post.publish.astimezone(pytz.timezone('America/Santiago'))
                redirect_url = reverse('landing:new_detail', kwargs={
                    'year': localized_publish.year,
                    'month': localized_publish.month,
                    'day': localized_publish.day,
                    'post': correct_slug
                })
                # Cachear la redirección
                cache.set(cache_key, f'redirect:{redirect_url}', 60 * 60 * 24)  # 24 horas
                return HttpResponseRedirect(redirect_url)

        # Cachear el post
        cache.set(cache_key, post, 60 * 60 * 6)  # 6 horas
        return post

    def get(self, request, *args, **kwargs):
        """Maneja las redirecciones correctamente"""
        self.object = self.get_object()

        if isinstance(self.object, HttpResponseRedirect):
            return self.object

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        """Contexto optimizado con cache"""
        context = super().get_context_data(**kwargs)
        current_lang = get_language()
        post = self.object

        # Cache de posts similares
        cache_key_similar = f'similar_posts_{post.pk}_{current_lang}'
        similar_posts = cache.get(cache_key_similar)

        if similar_posts is None:
            post_tags_ids = post.tags.values_list('id', flat=True)
            similar_posts = Post.published.filter(tags__in=post_tags_ids) \
                                .exclude(id=post.id) \
                                .annotate(same_tags=Count('tags')) \
                                .order_by('-same_tags', '-publish')[:4] \
                                .prefetch_related('translations', 'tags') \
                                .select_related('author', 'category')

            similar_posts = list(similar_posts)  # Convertir a lista para cachear
            cache.set(cache_key_similar, similar_posts, 60 * 60 * 2)  # 2 horas

        # Cache de tags populares
        cache_key_pop_tags = f'popular_tags_{current_lang}'
        popular_tags = cache.get(cache_key_pop_tags)

        if popular_tags is None:
            # Usar el mismo approach que en tu vista original
            popular_tags = list(Tag.objects.all()[:12])
            cache.set(cache_key_pop_tags, popular_tags, 60 * 60 * 4)  # 4 horas

        # Datos básicos del contexto
        context.update({
            'title': _('Noticias'),
            'subtitle': _('Infórmate sobre las últimas novedades de PYMEMAD.'),
            'refresh_captcha_url': reverse('landing:refresh_captcha'),
            'available_in_current_language': current_lang in post.get_available_languages(),
            'comment_form': CommentForm(),
            'tags': popular_tags,
            'post_tags': post.tags.all(),
            'comments': post.comments.filter(active=True),
            'similar_posts': similar_posts,
        })

        # Meta descripción
        post.set_current_language(current_lang)
        meta_description = post.safe_translation_getter('meta_description')
        if not meta_description and hasattr(post, 'get_meta_description'):
            meta_description = post.get_meta_description(lang=current_lang)

        context['meta_description'] = meta_description
        context['has_meta_description'] = bool(meta_description)

        # Posts anterior y siguiente (con cache)
        cache_key_nav = f'post_navigation_{post.pk}'
        nav_posts = cache.get(cache_key_nav)

        if nav_posts is None:
            nav_posts = {
                'previous': Post.published.filter(
                    publish__lt=post.publish
                ).order_by('-publish').first(),
                'next': Post.published.filter(
                    publish__gt=post.publish
                ).order_by('publish').first()
            }
            cache.set(cache_key_nav, nav_posts, 60 * 60)  # 1 hora

        context['previous_post'] = nav_posts['previous']
        context['next_post'] = nav_posts['next']

        # URLs por idioma
        scheme = self.request.scheme
        host = self.request.get_host()
        language_urls = {}

        for lang_code in post.get_available_languages():
            from django.utils.translation import activate
            activate(lang_code)

            try:
                translation = post.get_translation(lang_code)
                lang_slug = translation.slug
                localized_publish = post.publish.astimezone(pytz.timezone('America/Santiago'))

                path = reverse('landing:new_detail', kwargs={
                    'year': localized_publish.year,
                    'month': localized_publish.month,
                    'day': localized_publish.day,
                    'post': lang_slug
                })

                language_urls[lang_code] = f"{scheme}://{host}{path}"
            finally:
                activate(current_lang)

        context['language_urls'] = language_urls
        context['canonical_url'] = f"{scheme}://{host}{self.request.path}"

        return context


@method_decorator(never_cache, name='dispatch')
class CommentAjaxView(CreateView):
    """
    Vista basada en clases para manejar comentarios de posts via AJAX.
    """
    model = Comment
    form_class = CommentForm
    http_method_names = ['post']  # Solo permitir POST
    
    def dispatch(self, request, *args, **kwargs):
        """Override para verificar que es una petición AJAX"""
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('Petición no válida')
            }, status=400)
        return super().dispatch(request, *args, **kwargs)
    
    def get_post(self):
        """Obtiene el post relacionado con el comentario"""
        post_id = self.request.POST.get('post_id')
        if not post_id:
            return None
        
        try:
            return Post.published.get(id=post_id)
        except Post.DoesNotExist:
            return None
    
    def form_valid(self, form):
        """
        Maneja el caso en que el formulario es válido.
        """
        try:
            # Obtener el post
            post = self.get_post()
            if not post:
                return JsonResponse({
                    'success': False,
                    'message': _('Post no encontrado o ID no proporcionado')
                }, status=404)
            
            # Guardar el comentario
            comment = form.save(commit=False)
            comment.post = post
            comment.active = False  # Comentarios requieren aprobación
            comment.save()
            
            # Invalidar cache de comentarios del post
            cache.delete(f'post_comments_{post.pk}')
            
            # Generar nuevo captcha
            new_captcha_key = CaptchaStore.generate_key()
            
            return JsonResponse({
                'success': True,
                'message': _('Tu comentario ha sido enviado exitosamente y será publicado después de ser revisado por nuestro equipo.'),
                'action': 'message',  # Para que handleSuccess solo muestre el mensaje
                'comment_id': comment.id,
                'new_captcha_key': new_captcha_key,
                'new_captcha_image_url': captcha_image_url(new_captcha_key),
            }, status=200)
            
        except Exception as e:
            import traceback
            print("\n=== ERROR IN COMMENT FORM_VALID ===")
            traceback.print_exc()
            print(f"Error: {str(e)}")
            print("=== END ERROR ===\n")
            
            return JsonResponse({
                'success': False,
                'message': _('Ocurrió un error inesperado al procesar tu comentario. Por favor intenta nuevamente.'),
                'errors': [str(e)]
            }, status=500)
    
    def form_invalid(self, form):
        """
        Maneja el caso en que el formulario es inválido.
        """
        print("\n=== DEBUG COMMENT FORM INVALID ===")
        print("Form errors:", form.errors)
        print("Form data keys:", form.data.keys())
        
        # Debug específico de errores por campo
        for field, errors in form.errors.items():
            print(f"\nErrors for {field}:")
            for error in errors:
                print(f"  - {error}")
        
        print("=== END COMMENT FORM INVALID DEBUG ===\n")
        
        # Construir diccionario de errores con más información
        errors_dict = {}
        
        for field, errors in form.errors.items():
            # Obtener el campo del formulario
            if field == '__all__':
                field_label = 'General'
                field_id = 'general'
            else:
                field_obj = form.fields.get(field)
                if field_obj:
                    field_label = field_obj.label or field.replace('_', ' ').title()
                    field_id = field_obj.widget.attrs.get('id', f'id_{field}')
                else:
                    field_label = field.replace('_', ' ').title()
                    field_id = f'id_{field}'
            
            errors_list = [str(e) for e in errors]
            errors_dict[field] = {
                'field_name': field_label,
                'field_id': field_id,
                'messages': errors_list
            }
        
        # Generar nuevo captcha
        new_captcha_key = CaptchaStore.generate_key()
        
        return JsonResponse({
            'success': False,
            'message': _('Por favor corrige los siguientes errores:'),
            'errors': errors_dict,
            'new_captcha_key': new_captcha_key,
            'new_captcha_image_url': captcha_image_url(new_captcha_key),
        }, status=400)