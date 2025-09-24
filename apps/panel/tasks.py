# tasks.py
import json
import time
import markdown
import re

import markdown
from bs4 import BeautifulSoup
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management import call_command
from .ai import get_post_translation, generate_meta_descriptions_batch, get_post_ai
from .utils import segment_html_with_placeholders, reintegrate_translations, send_translation_complete_email, \
    send_translation_error_email

from apps.landing.models import Post


import logging

from ..accounts.forms import User

logger = logging.getLogger(__name__)


@shared_task(queue='long_tasks')
def generate_post_translations_task(post_id, user_id):
    """
    Tarea para generar traducciones con limpieza específica de cache
    """
    from apps.landing.models import Post
    from apps.panel.utils import clear_cache_for_post, clear_panel_cache

    try:
        post = Post.objects.get(pk=post_id)
        User = get_user_model()
        user = User.objects.get(pk=user_id)

        # Obtener contenido en español
        post.set_current_language('es')
        post_title_es = post.safe_translation_getter('title', default='').strip()
        post_body_es = post.safe_translation_getter('body', default='').strip()

        logger.info(f"Iniciando traducción del post {post_id}: {post_title_es[:50]}...")

        # Segmentar HTML para traducción
        segmented_html, placeholders = segment_html_with_placeholders(post_body_es)

        translations = {}

        # Traducir a cada idioma
        for lang_code, lang_name in [('en', 'English'), ('pt', 'Portuguese')]:
            logger.info(f"Traduciendo a {lang_name}...")

            title_translated, placeholders_translated = get_post_translation(
                title=post_title_es,
                placeholders=placeholders,
                target_language=lang_name
            )

            body_translated = reintegrate_translations(segmented_html, placeholders_translated)

            # Guardar traducción
            post.set_current_language(lang_code)
            post.title = title_translated
            post.body = body_translated
            post.slug = post._generate_unique_slug(lang_code, title_translated)
            post.save_translations()

            translations[f'title_{lang_code}'] = title_translated
            translations[f'body_{lang_code}'] = body_translated

        # Actualizar el post
        post.set_current_language('es')
        post.save(update_fields=['updated_at'])

        # # LIMPIAR CACHE ESPECÍFICO DEL POST
        # logger.info(f"Limpiando cache específico del post {post_id}")
        #
        # # Usar la función que ya tienes en signals.py
        # clear_cache_for_post(post_id)

        # NO llamar a clear_translation_cache() porque puede causar errores
        # El cache se limpiará con clear_cache_for_post()

        logger.info(f"Post {post_id} actualizado - Limpiando cache completamente...")

        # Limpiar cache del post con deep clean
        deleted_post = clear_cache_for_post(post, deep_clean=True)

        # Limpiar cache del panel
        deleted_panel = clear_panel_cache()

        # También limpiar cache de componentes relacionados
        from django.core.cache import cache
        cache.delete_many([
            'total_posts',
            'latest_posts',
            'recent_posts',
            'home_content',
        ])

        logger.info(f"✅ Cache limpiado: {deleted_post} claves del post, {deleted_panel} claves del panel")

        # Esperar un momento para propagación
        import time
        time.sleep(0.5)

        # Enviar correo - Comentado temporalmente por falta de servidor SMTP
        try:
            send_translation_complete_email(user.email, post_title_es, post_id)
        except Exception as email_err:
            logger.warning(f"No se pudo enviar email de notificación: {email_err}")
            # No fallar la tarea por error de email

        logger.info(f"Traducción completada para post {post_id}")

        return {
            "success": True,
            "post_id": post_id,
            "translations": translations,
            'cache_cleared': {
                'post_keys': deleted_post,
                'panel_keys': deleted_panel
            }
        }

    except Exception as err:
        logger.error(f"Error traduciendo post {post_id}: {str(err)}")
        # if user:
        #     send_translation_error_email(user.email, post_id, str(err))
        return {
            "success": False,
            "post_id": post_id,
            "error": str(err)
        }


@shared_task(queue='long_tasks')
def translate_existing_posts_task(start_id=0, continue_last=False):
    """
    Tarea de Celery para ejecutar el comando 'translate_existing_posts'
    que traduce automáticamente todos los posts pendientes
    """
    logger.info(
        f"Iniciando tarea de traducción de posts existentes. start_id={start_id}, continue_last={continue_last}")

    # Convertir argumentos a formato esperado por call_command
    options = {
        'start_id': start_id,
    }

    if continue_last:
        options['continue'] = True

    try:
        # Llamar al comando de Django con su nombre correcto
        # Asegúrate de que este nombre coincida con el nombre del archivo sin la extensión .py
        call_command('translate_existing_posts', **options)
        logger.info("Tarea de traducción de posts existentes completada con éxito")
        return {"success": True, "message": "Proceso de traducción completado"}
    except Exception as e:
        logger.error(f"Error en tarea de traducción de posts existentes: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task(queue='long_tasks')
def generate_all_metas_for_post(post_id):
    """
    Genera metas para todos los idiomas de un post.
    """
    try:
        post = Post.objects.get(pk=post_id)

        # Preparar datos
        post_data = {
            'id': post_id,
            'translations': {},
            'keywords': [tag.name for tag in post.tags.all()],
            'category': post.category.name if post.category else None
        }

        # Obtener traducciones
        for lang in ['es', 'en', 'pt']:
            if post.has_translation(lang):
                post.set_current_language(lang)
                post_data['translations'][lang] = {
                    'title': post.safe_translation_getter('title'),
                    'body': post.safe_translation_getter('body')
                }

        # Generar todas las metas de una vez
        results = generate_meta_descriptions_batch([post_data])

        if post_id in results:
            # Guardar cada meta
            for lang, meta in results[post_id].items():
                post.set_current_language(lang)
                post.meta_description = meta
                post.save_translations()

            # ELIMINAR O COMENTAR ESTAS LÍNEAS
            # Actualizar timestamp - COMENTADO PORQUE NO EXISTE EL CAMPO
            # post.meta_generated_at = timezone.now()
            # post.save(update_fields=['meta_generated_at'])

            logger.info(f"Metas generadas para post {post_id}: {list(results[post_id].keys())}")
            return results[post_id]
        return None

    except Exception as e:
        logger.error(f"Error generando metas para post {post_id}: {str(e)}")
        return None


@shared_task(queue='long_tasks')
def generate_meta_descriptions_task(start_id=0, continue_last=False, force=False):
    """
    Tarea de Celery para ejecutar el comando 'generate_meta_descriptions'
    que genera automáticamente meta descripciones SEO para todos los posts
    """
    logger.info(
        f"Iniciando tarea de generación de meta descripciones. "
        f"start_id={start_id}, continue_last={continue_last}, force={force}"
    )

    # Convertir argumentos a formato esperado por call_command
    options = {
        'start_id': start_id,
    }

    if continue_last:
        options['continue'] = True

    if force:
        options['force'] = True

    try:
        # Llamar al comando de Django
        call_command('generate_meta_descriptions', **options)
        logger.info("Tarea de generación de meta descripciones completada con éxito")
        return {
            "success": True,
            "message": "Proceso de generación de meta descripciones completado"
        }
    except Exception as e:
        logger.error(f"Error en tarea de generación de meta descripciones: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(bind=True, max_retries=3, queue='long_tasks')
def generate_post_ai_content_task(self, post_id, user_id, user_instructions=None):
    """
    Tarea de Celery para generar contenido AI para un post.
    """
    try:
        import re

        # Obtener el post y el usuario
        post = Post.objects.get(pk=post_id)
        user = User.objects.get(pk=user_id)

        logger.info(f"=" * 60)
        logger.info(f"INICIANDO GENERACIÓN AI PARA POST {post_id}")
        logger.info(f"Usuario: {user.username} (ID: {user_id})")
        logger.info(
            f"Instrucciones del usuario: {user_instructions if user_instructions else 'Sin instrucciones adicionales'}")

        # Validar que el post esté en estado borrador
        if post.status != "DRAFT":
            logger.error(f"Post {post_id} no está en borrador. Estado actual: {post.status}")
            raise ValueError("El post debe estar en estado borrador para generar contenido con IA")

        # Asegurarnos de usar la traducción en español
        post.set_current_language('es')

        # Obtener el cuerpo y título
        post_body = post.body if hasattr(post, 'body') else ""
        post_title = post.title if hasattr(post, 'title') else ""

        logger.info(
            f"Título obtenido: {post_title[:100]}..." if len(post_title) > 100 else f"Título obtenido: {post_title}")
        logger.info(f"Longitud del cuerpo HTML: {len(post_body)} caracteres")

        # Si no hay contenido en español, intentar con cualquier idioma
        if not post_body and not post_title:
            logger.warning("No hay contenido en español, intentando con cualquier idioma...")
            post_body = post.safe_translation_getter('body', any_language=True, default="")
            post_title = post.safe_translation_getter('title', any_language=True, default="")

        if not post_body and not post_title:
            logger.error("No se encontró contenido en ningún idioma")
            raise ValueError("No hay contenido disponible para generar la propuesta con IA")

        # Limpiar el HTML
        soup = BeautifulSoup(post_body, 'html.parser')
        post_ai_clean_html = soup.get_text(separator=' ', strip=True)

        logger.info(f"Texto limpio extraído: {len(post_ai_clean_html)} caracteres")
        logger.info(f"Primeros 200 caracteres del texto: {post_ai_clean_html[:200]}...")

        # Concatenar título y cuerpo
        complete_text = f"{post_title} {post_ai_clean_html}".strip()
        logger.info(f"Texto completo para AI: {len(complete_text)} caracteres")

        # Generar contenido con IA
        logger.info("Llamando a get_post_ai()...")
        new_post_ai = get_post_ai(
            body=complete_text,
            user_instructions=user_instructions
        )

        logger.info(f"Contenido recibido de AI (primeros 100 chars): {new_post_ai[:100]}...")

        # LIMPIEZA DEL CONTENIDO MARKDOWN
        # Eliminar los marcadores de código markdown
        cleaned_content = new_post_ai

        # Patrones a eliminar
        patterns_to_remove = [
            r'^```markdown\s*\n?',  # ```markdown al inicio
            r'^```\s*\n?',  # ``` al inicio
            r'\n?```\s*$',  # ``` al final
            r'\n?```markdown\s*$',  # ```markdown al final
        ]

        for pattern in patterns_to_remove:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE | re.MULTILINE)

        # Eliminar espacios en blanco extra al inicio y final
        cleaned_content = cleaned_content.strip()

        logger.info(f"Contenido limpiado (primeros 100 chars): {cleaned_content[:100]}...")

        # Convertir Markdown a HTML con configuración mejorada
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.codehilite',
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.attr_list'
        ])

        html_content = md.convert(cleaned_content)

        logger.info(f"HTML generado (primeros 200 chars): {html_content[:200]}...")

        # Guardar el contenido generado (opcional)
        # Puedes crear un modelo para almacenar propuestas AI o guardarlo en el post

        # Enviar email de notificación - con manejo de errores
        try:
            subject = f"Contenido AI generado para: {post_title}"
            message = f"""
            Hola {user.get_full_name() or user.username},

            El contenido AI para tu post "{post_title}" ha sido generado exitosamente.

            Puedes revisar y editar el contenido en el panel de administración.

            Saludos,
            El equipo de {settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'AcoforagWeb'}
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            logger.info("Email de notificación enviado")
        except Exception as email_err:
            logger.warning(f"No se pudo enviar email de notificación: {email_err}")

        logger.info(f"Contenido AI generado exitosamente para post {post_id}")
        logger.info(f"=" * 60)

        return {
            'success': True,
            'post_id': post_id,
            'content': cleaned_content,  # Contenido markdown limpio
            'html_content': html_content  # HTML procesado
        }

    except Exception as e:
        logger.error(f"Error generando contenido AI para post {post_id}: {str(e)}")
        logger.error(f"=" * 60)

        # Reintentar la tarea
        if self.request.retries < self.max_retries:
            logger.info(f"Reintentando tarea (intento {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        # Enviar email de error
        try:
            user = User.objects.get(pk=user_id)
            send_mail(
                f"Error generando contenido AI",
                f"Hubo un error al generar el contenido AI: {str(e)}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except:
            pass

        raise
