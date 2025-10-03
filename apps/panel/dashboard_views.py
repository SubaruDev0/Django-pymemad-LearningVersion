from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.translation import get_language
from django.views import View
from django_filters.views import FilterView
from django.http import JsonResponse
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from datetime import timedelta
from django.utils.dateparse import parse_date
import pandas as pd
import tempfile
import os

from apps.landing.models import ContactMessage
from apps.panel.filters import ContactMessageFilter
from apps.permissions.mixins import ACLPermissionMixin

class DashBoardView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'dashboard'
    required_action = 'view'

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

        return render(request, 'dashboard.html', context)

class MembersView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'members'
    required_action = 'view'

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

        return render(request, 'members.html', context)

class BillingView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'billing'
    required_action = 'view'

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

        return render(request, 'billing.html', context)

class ExpensesView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'expenses'
    required_action = 'view'

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

        return render(request, 'expenses.html', context)

class BalanceView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'balance'
    required_action = 'view'

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

        return render(request, 'balance.html', context)

class PlanView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'strategy'
    required_action = 'view'
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

        return render(request, 'plan.html', context)

# =====================================================================
# VISTAS DE GESTIÓN DE CONTACTOS
# =====================================================================


@method_decorator(never_cache, name='dispatch')
class ContactMessageListView(ACLPermissionMixin, LoginRequiredMixin, FilterView):
    module_code = 'contacts'
    required_action = 'view'
    """
    Vista para listar y filtrar mensajes de contacto con soporte para DataTables server-side.
    """
    model = ContactMessage
    template_name = 'contacts-list.html'
    context_object_name = 'contacts'
    filterset_class = ContactMessageFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filterset = None
        self.object_list = None

    def get_queryset(self):
        return ContactMessage.objects.select_related().order_by('-created_at')

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        data = self.request.GET.copy()
        kwargs['data'] = data
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ✅ OBTENER EL QUERYSET FILTRADO POR EL FilterSet
        filtered_qs = self.get_filterset(self.filterset_class).qs

        # ✅ Estadísticas basadas en el queryset filtrado
        context['total_contacts'] = filtered_qs.count()
        context['unread_contacts'] = filtered_qs.filter(is_read=False).count()
        context['unanswered_contacts'] = filtered_qs.filter(is_answered=False).count()

        # ✅ Datos para gráficos (por tema) basados en el queryset filtrado
        subject_stats = {}
        for subject_code, subject_name in ContactMessage.SUBJECT_CHOICES:
            count = filtered_qs.filter(subject=subject_code).count()
            if count > 0:  # Solo incluir temas con contactos
                subject_stats[subject_name] = count

        # ✅ Timeline basado en el queryset filtrado
        context['chart_data'] = {
            'subjects': {
                'labels': list(subject_stats.keys()),
                'data': list(subject_stats.values())
            },
            'timeline': self.get_timeline_data(filtered_qs),
        }

        context.update({
            'title_page': 'Gestión de Contactos',
            'subject_stats': subject_stats,
        })
        return context
    
    def get_timeline_data(self, queryset):
        """Genera datos para el gráfico de línea temporal (últimos 30 días)"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        daily_counts = queryset.filter(
            created_at__date__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        dates = []
        counts = []
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
        return date.strftime('%Y-%m-%d %H:%M') if date else '-'

    def render_to_response(self, context, **response_kwargs):
        """
        Responde solicitudes AJAX con datos JSON para DataTables.
        """
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Obtener filtros desde la petición
            subject = self.request.GET.get('subject')
            is_read = self.request.GET.get('is_read')
            is_answered = self.request.GET.get('is_answered')
            date_range = self.request.GET.get('created_date_range')

            # Iniciar con todos los contactos
            queryset = ContactMessage.objects.all()

            # Aplicar filtros
            if subject:
                queryset = queryset.filter(subject=subject)
            if is_read and is_read != '':
                # Convertir el valor string a booleano
                if is_read == 'True' or is_read == 'true' or is_read == '1':
                    queryset = queryset.filter(is_read=True)
                elif is_read == 'False' or is_read == 'false' or is_read == '0':
                    queryset = queryset.filter(is_read=False)
            if is_answered and is_answered != '':
                # Convertir el valor string a booleano
                if is_answered == 'True' or is_answered == 'true' or is_answered == '1':
                    queryset = queryset.filter(is_answered=True)
                elif is_answered == 'False' or is_answered == 'false' or is_answered == '0':
                    queryset = queryset.filter(is_answered=False)
            if date_range:
                try:
                    dates = date_range.split(' a ')
                    if len(dates) == 2:
                        start_date = parse_date(dates[0].strip())
                        end_date = parse_date(dates[1].strip())
                        if start_date and end_date:
                            queryset = queryset.filter(created_at__date__range=(start_date, end_date))
                except (ValueError, IndexError):
                    pass

            draw = int(self.request.GET.get('draw', 1))
            start = int(self.request.GET.get('start', 0))
            length = int(self.request.GET.get('length', 10))
            search_value = self.request.GET.get('search[value]', '')

            # Columnas para ordenamiento
            column_list = [
                None,           # checkbox
                'name',         # nombre
                'email',        # email
                'company',      # empresa
                'subject',      # tema
                'created_at',   # fecha
                None            # acciones
            ]

            # Ordenamiento
            order_column = int(self.request.GET.get('order[0][column]', 5))
            order_dir = self.request.GET.get('order[0][dir]', 'desc')
            if order_column < len(column_list) and column_list[order_column]:
                order_field = column_list[order_column]
                if order_dir == 'desc':
                    order_field = '-' + order_field
            else:
                order_field = '-created_at'

            # Total sin filtro
            records_total = queryset.count()

            # Búsqueda global
            if search_value:
                queryset = queryset.filter(
                    Q(name__icontains=search_value) |
                    Q(email__icontains=search_value) |
                    Q(company__icontains=search_value) |
                    Q(phone__icontains=search_value) |
                    Q(message__icontains=search_value)
                ).distinct()
                records_filtered = queryset.count()
            else:
                records_filtered = records_total

            # Paginación y ordenamiento
            queryset = queryset.order_by(order_field)[start:start + length]

            data = []
            for contact in queryset:
                message_preview = contact.message[:100] + '...' if len(contact.message) > 100 else contact.message
                data.append({
                    "id": contact.pk,
                    "name": contact.name,
                    "email": contact.email,
                    "company": contact.company or "-",
                    "subject": contact.get_subject_display(),
                    "is_read": contact.is_read,
                    "is_answered": contact.is_answered,
                    "status": "",  # Se renderiza en el frontend
                    "created_at": self.format_date(contact.created_at),
                    "message": message_preview,
                    "actions": mark_safe(
                        f'''
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-info text-white view-contact"
                                data-id="{contact.pk}"
                                data-name="{contact.name}"
                                data-email="{contact.email}"
                                data-phone="{contact.phone or 'No especificado'}"
                                data-company="{contact.company or 'No especificada'}"
                                data-subject="{contact.get_subject_display()}"
                                data-message="{contact.message}"
                                data-date="{self.format_date(contact.created_at)}"
                                title="Ver detalles">
                                <i class="ai-show"></i>
                            </button>
                            <button class="btn btn-sm btn-success text-white answer-contact"
                                data-id="{contact.pk}"
                                data-email="{contact.email}"
                                data-name="{contact.name}"
                                title="Responder mensaje">
                                <i class="ai-messages"></i>
                            </button>
                        </div>
                        '''
                    )
                })

            return JsonResponse({
                'draw': draw,
                'recordsTotal': records_total,
                'recordsFiltered': records_filtered,
                'data': data
            })

        return super().render_to_response(context, **response_kwargs)
@method_decorator(never_cache, name='dispatch')
class ContactMessageDeleteView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'contacts'
    required_action = 'delete'
    """
    Vista para eliminar un mensaje de contacto específico.
    """
    def delete(self, request, *args, **kwargs):
        try:
            contact_id = kwargs.get('pk')
            contact = ContactMessage.objects.get(pk=contact_id)
            contact.delete()
            return JsonResponse({
                'success': True,
                'message': 'Contacto eliminado correctamente'
            })
        except ContactMessage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Contacto no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar contacto: {str(e)}'
            }, status=500)

@method_decorator(never_cache, name='dispatch')
class ContactMessageExportView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'contacts'
    required_action = 'export'
    """
    Vista para exportar contactos en formato Excel
    """
    def post(self, request, *args, **kwargs):
        try:
            # Obtener los IDs de contactos desde los datos POST
            contact_ids = request.POST.getlist('contact_ids[]')
            if not contact_ids:
                contact_ids = request.POST.getlist('contact_ids')

            # Si no hay IDs específicos, exportar todos los contactos (con filtros si se proporcionan)
            if not contact_ids:
                # Iniciar con todos los contactos
                contacts = ContactMessage.objects.all()
                # Aplicar filtros si se proporcionan
                subject = request.POST.get('subject')
                date_range = request.POST.get('created_date_range')
                if subject:
                    contacts = contacts.filter(subject=subject)
                if date_range:
                    try:
                        # Parsear el rango de fechas (formato: "YYYY-MM-DD a YYYY-MM-DD")
                        dates = date_range.split(' a ')
                        if len(dates) == 2:
                            start_date = parse_date(dates[0].strip())
                            end_date = parse_date(dates[1].strip())
                            if start_date and end_date:
                                contacts = contacts.filter(
                                    created_at__date__range=(start_date, end_date)
                                )
                    except Exception as e:
                        print(f"[Export Warning] Error parsing date range: {e}")
                contacts = contacts.order_by('-created_at')
            else:
                # Convertir IDs a enteros
                contact_ids = [int(cid) for cid in contact_ids]
                contacts = ContactMessage.objects.filter(pk__in=contact_ids)

            if not contacts.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'No se encontraron contactos para exportar'
                }, status=404)

            # Preparar los datos para el DataFrame
            data = []
            for contact in contacts:
                row = {
                    'ID': contact.pk,
                    'Nombre': contact.name,
                    'Email': contact.email,
                    'Teléfono': contact.phone or "-",
                    'Empresa': contact.company or "-",
                    'Tema': contact.get_subject_display(),
                    'Mensaje': contact.message,
                    'Fecha': contact.created_at.strftime('%d-%m-%Y %H:%M') if contact.created_at else '',
                    'Leído': 'Sí' if contact.is_read else 'No',
                    'Respondido': 'Sí' if contact.is_answered else 'No',
                }
                data.append(row)

            # Crear DataFrame
            df = pd.DataFrame(data)

            # Crear archivo temporal para el Excel
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp:
                # Escribir Excel con formato
                with pd.ExcelWriter(temp.name, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Contactos', index=False)
                    # Obtener el workbook y worksheet para formato
                    workbook = writer.book
                    worksheet = writer.sheets['Contactos']
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
                        # Establecer un ancho máximo para la columna de mensaje
                        if column == 'Mensaje':
                            worksheet.set_column(i, i, min(column_len, 80))
                        else:
                            worksheet.set_column(i, i, min(column_len, 50))
                    # Congelar primera fila
                    worksheet.freeze_panes(1, 0)
                # Rebobinar el archivo temporal
                temp.seek(0)

                # Generar nombre de archivo
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                filename = f"contactos_export_{timestamp}"

                # Subir archivo a S3
                from apps.panel.utils import save_file_to_s3
                excel_url = save_file_to_s3(
                    temp,
                    filename=filename,
                    folder_path="exports/contactos",
                    file_extension="xlsx",
                    add_timestamp=False  # ya lo incluimos en filename
                )

                # Limpiar archivo temporal
                os.unlink(temp.name)

                if not excel_url:
                    return JsonResponse({
                        'success': False,
                        'message': 'Error al subir el archivo a S3'
                    }, status=500)

                # Retornar URL del archivo en S3
                return JsonResponse({
                    'success': True,
                    'file_path': excel_url,
                    'filename': f"{filename}.xlsx",
                    'total_contacts': len(data),
                    'message': f'Archivo generado exitosamente con {len(data)} contactos.',
                    'download_url': excel_url
                })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error al exportar contactos: {str(e)}'
            }, status=500)

# Para marcar un contacto como leido o no
from django.views import View
from django.http import JsonResponse

@method_decorator(never_cache, name='dispatch')
class ContactMarkReadView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'contacts'
    required_action = 'change'
    """
    Vista para marcar un contacto como leído
    """
    def post(self, request, *args, **kwargs):
        try:
            contact_id = kwargs.get('pk')
            contact = ContactMessage.objects.get(pk=contact_id)
            contact.is_read = True
            contact.save()
            return JsonResponse({
                'success': True,
                'message': 'Contacto marcado como leído'
            })
        except ContactMessage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Contacto no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al marcar como leído: {str(e)}'
            }, status=500)

from django.views import View
from django.http import JsonResponse
from apps.landing.models import ContactReply

@method_decorator(never_cache, name='dispatch')
class ContactRepliesView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'contacts'
    required_action = 'view'
    """
    Vista para obtener las respuestas de un contacto específico.
    """
    def get(self, request, *args, **kwargs):
        try:
            contact_id = kwargs.get('pk')
            contact = ContactMessage.objects.get(pk=contact_id)

            # Obtener todas las respuestas
            replies = ContactReply.objects.filter(
                contact_message=contact
            ).order_by('sent_at')

            # Serializar las respuestas
            replies_data = []
            for reply in replies:
                replies_data.append({
                    'id': reply.pk,
                    'subject': reply.subject,
                    'message': reply.message,
                    'sent_by': reply.sent_by.get_full_name() if reply.sent_by else 'Sistema',
                    'sent_at': reply.sent_at.strftime('%d/%m/%Y %H:%M'),
                    'email_sent': reply.email_sent,
                })

            return JsonResponse({
                'success': True,
                'replies': replies_data,
                'total': len(replies_data)
            })

        except ContactMessage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Contacto no encontrado',
                'replies': []
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al obtener respuestas: {str(e)}',
                'replies': []
            }, status=500)

@method_decorator(never_cache, name='dispatch')
class ContactMessageAnswerView(ACLPermissionMixin, LoginRequiredMixin, View):
    module_code = 'contacts'
    required_action = 'change'
    """
    Guarda la respuesta y envía el email al contacto.
    """
    def post(self, request, *args, **kwargs):
        try:
            contact_id = kwargs.get('pk')
            contact = ContactMessage.objects.get(pk=contact_id)

            # Obtener datos de la respuesta
            email = request.POST.get('email', contact.email)
            subject = request.POST.get('subject', f'Re: {contact.get_subject_display()}')
            message = request.POST.get('message', '')

            # Crear y guardar la respuesta
            reply = ContactReply.objects.create(
                contact_message=contact,
                subject=subject,
                message=message,
                sent_by=request.user if request.user.is_authenticated else None
            )

            # Preparar datos para el email
            reply_data = {
                'name': contact.name,
                'email': email,
                'subject': subject,
                'message': message,
                'original_message': contact.message[:500]  # Primeros 500 caracteres del mensaje original
            }

            # Enviar email usando Celery
            try:
                from apps.landing.tasks import send_contact_reply_email_task
                result = send_contact_reply_email_task.delay(reply_data)
                reply.email_sent = True
                reply.save()
            except Exception as e:
                reply.email_error = str(e)
                reply.save()
                # Log pero continuar - el email puede fallar pero la respuesta se guardó
                print(f"Error enviando email de respuesta: {str(e)}")

            # Marcar contacto como respondido
            contact.is_answered = True
            contact.save()

            return JsonResponse({
                'success': True,
                'message': 'Respuesta enviada y guardada correctamente'
            })

        except ContactMessage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Contacto no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al procesar respuesta: {str(e)}'
            }, status=500)