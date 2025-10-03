# apps/landing/tasks.py - Tareas asíncronas para la app landing
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


# ========== TAREAS DE EMAIL DE CONTACTO ========== #

@shared_task(queue='short_tasks')
def send_contact_email_task(contact_data):
    """
    Tarea asíncrona para enviar un correo con los detalles del formulario de contacto de PymeMad.
    """
    template = get_template('email/contact_notification_email.html')

    # Crear el contexto para la plantilla
    ctx = {
        'name': contact_data['name'],
        'email': contact_data['email'],
        'phone': contact_data['phone'],
        'company': contact_data['company'],
        'subject': contact_data['subject'],
        'message': contact_data['message'],
    }

    contenido = template.render(ctx)

    # Configurar destinatarios - ajustar según necesidades
    recipients = [
        # 'contacto@pymemad.cl',
        # 'info@pymemad.cl',
        'yllorca@helloworld.cl',  # Para testing
    ]

    # Crear el mensaje de email
    msg = EmailMultiAlternatives(
        subject=f'Nuevo Contacto PymeMad - {contact_data["subject"]}',
        body=contenido,
        from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@pymemad.cl',
        to=recipients,
    )
    msg.attach_alternative(contenido, "text/html")

    try:
        msg.send()
        logger.info(f"Email de contacto enviado exitosamente a {recipients}")
    except Exception as e:
        logger.error(f"Error al enviar email de contacto: {str(e)}")
        raise


@shared_task(queue='short_tasks')
def send_contact_confirmation_email_task(contact_data):
    """
    Tarea opcional para enviar email de confirmación al usuario que llenó el formulario.
    """
    template = get_template('email/contact_confirmation_email.html')

    # Crear el contexto para la plantilla
    ctx = {
        'name': contact_data['name'],
        'subject': contact_data['subject'],
    }

    contenido = template.render(ctx)

    # Crear el mensaje de email
    msg = EmailMultiAlternatives(
        subject='Hemos recibido tu mensaje - PymeMad',
        body=contenido,
        from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@pymemad.cl',
        to=[contact_data['email']],
    )
    msg.attach_alternative(contenido, "text/html")

    try:
        msg.send()
        logger.info(f"Email de confirmación enviado a {contact_data['email']}")
    except Exception as e:
        logger.error(f"Error al enviar email de confirmación: {str(e)}")


@shared_task(queue='short_tasks')
def send_contact_reply_email_task(reply_data):
    """
    Tarea Celery para enviar respuestas a mensajes de contacto
    """
    try:
        # Renderizar el template
        template = get_template('email/contact_reply_email.html')
        ctx = {
            'name': reply_data['name'],
            'subject': reply_data['subject'],
            'message': reply_data['message'],
            'original_message': reply_data.get('original_message', ''),
        }

        contenido = template.render(ctx)

        # Crear el mensaje de email
        msg = EmailMultiAlternatives(
            subject=reply_data['subject'],
            body=contenido,
            from_email=settings.DEFAULT_FROM_EMAIL or 'contacto@pymemad.cl',
            to=[reply_data['email']],
        )
        msg.attach_alternative(contenido, "text/html")

        # Enviar el email
        msg.send(fail_silently=False)

        logger.info(f"Respuesta enviada exitosamente a {reply_data['email']}")
        return True

    except Exception as e:
        logger.error(f"Error al enviar respuesta: {str(e)}")
        return False
