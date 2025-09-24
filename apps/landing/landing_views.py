from django.shortcuts import render, redirect
from django.utils.translation import gettext as _, get_language
from django.views import View
from django.http import JsonResponse
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url
from apps.landing.models import Post
from apps.landing.forms import ContactForm


# ========== VISTA HOME OPTIMIZADA ========== #
@method_decorator(cache_page(settings.CACHE_TIMES.get('home', 3600)), name='dispatch')
@method_decorator(vary_on_headers('Accept-Language'), name='dispatch')
class HomeView(View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Cache key para datos del home
        cache_key = f'home_data_{language}'
        context_data = cache.get(cache_key)

        if context_data is None:
            # Obtener los últimos 3 posts publicados
            latest_posts = Post.published.all().select_related('author', 'category').prefetch_related('translations', 'tags')[:3]
            
            context_data = {
                'latest_posts': list(latest_posts),
            }
            
            # Cachear por 1 hora
            cache.set(cache_key, context_data, 60 * 60)

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()
        path = self.request.path

        # Construir la URL base correctamente
        canonical_url = f"{scheme}://{host}{path}"

        # Combinar contexto cacheado con datos dinámicos
        context = context_data.copy()
        context['canonical_url'] = canonical_url

        return render(request, 'home.html', context)


class AboutView(View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'about_us.html', context)


class MembersView(View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'members_directory.html', context)


class NewsView(View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'news.html', context)


class MagazineView(View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'magazine.html', context)


class ContactView(View):
    """
    Vista simplificada para manejar la creación de mensajes de contacto.
    """

    def get(self, request, *args, **kwargs):
        """Maneja las peticiones GET - muestra el formulario"""
        form = ContactForm()

        # URL canónica para SEO
        scheme = request.scheme
        host = request.get_host()
        path = request.path
        canonical_url = f"{scheme}://{host}{path}"

        context = {
            'form': form,
            'title': _('Contacto - PymeMad'),
            'page_title': _('¿Cómo podemos ayudarte?'),
            'description': _(
                'Completa el formulario o contáctanos directamente a través de nuestros canales de comunicación.'),
            'button_text': _('Enviar mensaje'),
            'canonical_url': canonical_url,
            'form_action': reverse('landing:contact'),
            'refresh_captcha_url': reverse('landing:refresh_captcha'),
        }

        return render(request, 'contact.html', context)

    def post(self, request, *args, **kwargs):
        """Maneja las peticiones POST - procesa el formulario"""
        form = ContactForm(request.POST)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        print("\n=== DEBUG CONTACT POST ===")
        print("Is AJAX:", is_ajax)
        print("POST data keys:", request.POST.keys())

        if form.is_valid():
            try:
                # Guardar el contacto
                contact = form.save()

                print(f"Contact saved: ID={contact.pk}, Name={contact.name}")

                # Preparar datos para el email
                contact_data = {
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone or "No especificado",
                    'company': contact.company or "No especificada",
                    'subject': contact.get_subject_display(),
                    'message': contact.message,
                }

                # Agregar dirección IP
                contact.ip_address = request.META.get('REMOTE_ADDR')
                contact.save()

                # Enviar tareas de email
                try:
                    # Importar tasks dinámicamente
                    from apps.landing.tasks import send_contact_email_task, send_contact_confirmation_email_task

                    # Enviar email a los administradores
                    send_contact_email_task.delay(contact_data)
                    print("Email task sent successfully to administrators")
                    # # Enviar email de confirmación al usuario
                    # send_contact_confirmation_email_task.delay(contact_data)
                    # print(f"Confirmation email task sent to {contact.email}")
                except ImportError:
                    print("Email tasks not available - tasks module not found")
                except Exception as e:
                    print(f"Error sending email tasks: {str(e)}")

                # Si es AJAX, devolver JSON
                if is_ajax:
                    # Generar nuevo captcha
                    new_captcha_key = CaptchaStore.generate_key()

                    return JsonResponse({
                        'success': True,
                        'message': _(
                            'Muchas gracias por tu mensaje. Hemos recibido tu consulta y te responderemos dentro de las próximas 24 horas hábiles.'),
                        'action': 'message',
                        'new_captcha_key': new_captcha_key,
                        'new_captcha_image_url': captcha_image_url(new_captcha_key),
                    })
                else:
                    return redirect('landing:contact')

            except Exception as e:
                print(f"Error saving contact: {str(e)}")

                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': _('Error al procesar tu mensaje. Por favor intenta nuevamente.'),
                        'errors': [str(e)]
                    }, status=500)
                else:
                    from django.contrib import messages
                    messages.error(request, _('Error al enviar el mensaje'))

        else:
            # Formulario inválido
            print("Form errors:", form.errors)

            if is_ajax:
                # Construir diccionario de errores
                errors_dict = {}
                for field, errors in form.errors.items():
                    if field == '__all__':
                        field_label = 'General'
                        field_id = 'general'
                    else:
                        field_obj = form.fields.get(field)
                        if field_obj:
                            field_label = field_obj.label or field.replace('_', ' ').title()
                            field_id = f'id_{field}'
                        else:
                            field_label = field.replace('_', ' ').title()
                            field_id = f'id_{field}'

                    errors_dict[field] = {
                        'field_name': field_label,
                        'field_id': field_id,
                        'messages': [str(e) for e in errors]
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

        # Si no es AJAX y hay errores, mostrar el formulario con errores
        context = {
            'form': form,
            'title': _('Contacto - Loginfor'),
            'page_title': _('¿Cómo podemos ayudarte?'),
            'description': _(
                'Completa el formulario o contáctanos directamente a través de nuestros canales de comunicación.'),
            'button_text': _('Enviar mensaje'),
            'canonical_url': f"{request.scheme}://{request.get_host()}{request.path}",
            'form_action': reverse('landing:contact'),
            'refresh_captcha_url': reverse('landing:refresh_captcha'),
        }

        return render(request, 'contact.html', context)


class JoinView(View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'join.html', context)


@never_cache
def refresh_captcha(request):
    """
    Vista para refrescar el captcha vía AJAX.
    """
    try:
        # Usar el método correcto para generar un nuevo captcha
        new_captcha_key = CaptchaStore.generate_key()
        new_captcha_image_url = captcha_image_url(new_captcha_key)
        print("new_captcha_image_url", new_captcha_image_url)

        response = {
            'success': True,
            'captcha_key': new_captcha_key,
            'captcha_image': new_captcha_image_url,
        }

        return JsonResponse(response)
        
    except Exception as e:
        print(f"Error refreshing captcha: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
