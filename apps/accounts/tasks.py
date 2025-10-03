# apps/accounts/tasks.py
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth import get_user_model
import logging
logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(queue='short_tasks', max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(user_id, domain, use_https=True):
    try:
        user = User.objects.get(pk=user_id)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        context = {
            'email': user.email,
            'domain': domain,
            'site_name': 'PymeMad',
            'uid': uid,
            'user': user,
            'token': token,
            'protocol': 'https' if use_https else 'http',
        }
        subject = render_to_string('email/password_reset_subject.txt', context)
        subject = ''.join(subject.splitlines())
        html_content = render_to_string('email/password_reset_email.html', context)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@pymemad.cl',
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Email de recuperación enviado exitosamente a {user.email}")
        return {'success': True, 'email': user.email}
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado")
        return {'success': False, 'error': f'Usuario con ID {user_id} no encontrado'}
    except Exception as e:
        logger.error(f"Error al enviar email de recuperación: {str(e)}")
        raise send_password_reset_email_task.retry(exc=e)

@shared_task(queue='short_tasks')
def send_password_reset_confirmation_email_task(user_id):
    try:
        user = User.objects.get(pk=user_id)
        context = {
            'user': user,
            'site_name': 'PymeMad',
            'domain': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'pymemad.cl',
            'protocol': 'https'
        }
        html_content = render_to_string('email/password_changed_email.html', context)
        msg = EmailMultiAlternatives(
            subject='✅ Tu contraseña ha sido actualizada',
            body='Tu contraseña ha sido actualizada exitosamente.',
            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@pymemad.cl',
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Email de confirmación enviado a {user.email}")
        return {'success': True, 'email': user.email}
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado")
        return {'success': False, 'error': f'Usuario con ID {user_id} no encontrado'}
    except Exception as e:
        logger.error(f"Error al enviar email de confirmación: {str(e)}")
        return {'success': False, 'error': str(e)}