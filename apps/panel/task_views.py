"""
Vistas para la gestión de tareas en el panel de administración
Este módulo contiene todas las vistas relacionadas con tareas
"""

# =====================================================================
# IMPORTACIONES ESTÁNDAR DE PYTHON
# =====================================================================
import json
from datetime import datetime, timedelta

# =====================================================================
# IMPORTACIONES DE TERCEROS
# =====================================================================
from celery.result import AsyncResult

# =====================================================================
# IMPORTACIONES DE DJANGO
# =====================================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView

# =====================================================================
# IMPORTACIONES LOCALES
# =====================================================================
from apps.panel.models import Task
from apps.panel.tasks import (
    translate_post_task,
    generate_ai_content_task,
    export_posts_to_excel_task,
    cleanup_old_tasks
)


# =====================================================================
# =====================================================================
#                    SECCIÓN 1: VISTAS DE LISTADO
# =====================================================================
# =====================================================================

class TaskListView(LoginRequiredMixin, ListView):
    """
    Vista para listar todas las tareas del usuario
    """
    model = Task
    template_name = 'panel/tasks/list.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        """
        Obtiene las tareas del usuario actual
        """
        queryset = Task.objects.filter(user=self.request.user)
        
        # Filtro por estado
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filtro por tipo
        task_type = self.request.GET.get('type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de tareas
        context['stats'] = {
            'pending': self.get_queryset().filter(status='PENDING').count(),
            'progress': self.get_queryset().filter(status='PROGRESS').count(),
            'success': self.get_queryset().filter(status='SUCCESS').count(),
            'failure': self.get_queryset().filter(status='FAILURE').count(),
        }
        
        # Filtros actuales
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'type': self.request.GET.get('type', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        # Tipos de tareas disponibles
        context['task_types'] = [
            ('translation', 'Traducción'),
            ('ai_generation', 'Generación IA'),
            ('export', 'Exportación'),
            ('import', 'Importación'),
            ('cleanup', 'Limpieza'),
        ]
        
        return context


# =====================================================================
# =====================================================================
#                    SECCIÓN 2: DETALLE Y ESTADO
# =====================================================================
# =====================================================================

class TaskDetailView(LoginRequiredMixin, DetailView):
    """
    Vista para ver el detalle de una tarea
    """
    model = Task
    template_name = 'panel/tasks/detail.html'
    context_object_name = 'task'
    
    def get_queryset(self):
        """
        Solo tareas del usuario actual
        """
        return Task.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el resultado de Celery si existe
        if self.object.celery_task_id:
            result = AsyncResult(self.object.celery_task_id)
            context['celery_info'] = {
                'state': result.state,
                'info': result.info if isinstance(result.info, dict) else str(result.info),
                'ready': result.ready(),
                'successful': result.successful() if result.ready() else None,
            }
        
        # Calcular duración si la tarea terminó
        if self.object.completed_at and self.object.started_at:
            duration = self.object.completed_at - self.object.started_at
            context['duration'] = duration
        
        # Parsear el resultado si es JSON
        if self.object.result:
            try:
                context['result_json'] = json.loads(self.object.result)
            except:
                context['result_json'] = None
        
        return context


@login_required
def task_status(request, pk):
    """
    Vista AJAX para obtener el estado actual de una tarea
    """
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    # Actualizar estado desde Celery
    if task.celery_task_id and task.status in ['PENDING', 'PROGRESS']:
        result = AsyncResult(task.celery_task_id)
        
        if result.state == 'SUCCESS':
            task.status = 'SUCCESS'
            task.result = str(result.result)
            task.completed_at = timezone.now()
            task.save()
        elif result.state == 'FAILURE':
            task.status = 'FAILURE'
            task.error = str(result.info)
            task.completed_at = timezone.now()
            task.save()
        elif result.state == 'PROGRESS':
            task.status = 'PROGRESS'
            if isinstance(result.info, dict):
                task.progress = result.info.get('current', 0)
                task.progress_total = result.info.get('total', 100)
            task.save()
    
    # Preparar respuesta
    response_data = {
        'id': task.id,
        'status': task.status,
        'progress': task.progress,
        'progress_total': task.progress_total,
        'name': task.name,
        'created_at': task.created_at.isoformat(),
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
    }
    
    if task.status == 'SUCCESS' and task.result:
        try:
            response_data['result'] = json.loads(task.result)
        except:
            response_data['result'] = task.result
    
    if task.status == 'FAILURE' and task.error:
        response_data['error'] = task.error
    
    return JsonResponse(response_data)


# =====================================================================
# =====================================================================
#                    SECCIÓN 3: ACCIONES DE TAREAS
# =====================================================================
# =====================================================================

@login_required
def retry_task(request, pk):
    """
    Reintentar una tarea fallida
    """
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if task.status != 'FAILURE':
        messages.warning(request, 'Solo se pueden reintentar tareas fallidas.')
        return redirect('panel:task-detail', pk=task.pk)
    
    # Crear nueva tarea basada en la anterior
    new_task = Task.objects.create(
        user=task.user,
        name=f"{task.name} (Reintento)",
        description=task.description,
        task_type=task.task_type,
        status='PENDING',
        retry_of=task
    )
    
    # Ejecutar según el tipo de tarea
    if task.task_type == 'translation':
        # Extraer el post_id del contexto
        try:
            context = json.loads(task.context) if task.context else {}
            post_id = context.get('post_id')
            if post_id:
                result = translate_post_task.delay(post_id, request.user.email)
                new_task.celery_task_id = result.id
                new_task.save()
        except Exception as e:
            new_task.status = 'FAILURE'
            new_task.error = str(e)
            new_task.save()
    
    messages.success(request, 'Tarea reiniciada correctamente.')
    return redirect('panel:task-detail', pk=new_task.pk)


@login_required
def cancel_task(request, pk):
    """
    Cancelar una tarea en progreso
    """
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if task.status not in ['PENDING', 'PROGRESS']:
        messages.warning(request, 'Solo se pueden cancelar tareas pendientes o en progreso.')
        return redirect('panel:task-detail', pk=task.pk)
    
    # Cancelar en Celery si existe
    if task.celery_task_id:
        from apps.core.celery import app
        app.control.revoke(task.celery_task_id, terminate=True)
    
    # Actualizar estado
    task.status = 'CANCELLED'
    task.completed_at = timezone.now()
    task.save()
    
    messages.success(request, 'Tarea cancelada correctamente.')
    return redirect('panel:task-detail', pk=task.pk)


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar una tarea
    """
    model = Task
    template_name = 'panel/tasks/delete.html'
    success_url = reverse_lazy('panel:task-list')
    
    def get_queryset(self):
        """
        Solo tareas del usuario actual
        """
        return Task.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Tarea eliminada correctamente.')
        return super().delete(request, *args, **kwargs)


# =====================================================================
# =====================================================================
#                    SECCIÓN 4: ACCIONES MASIVAS
# =====================================================================
# =====================================================================

@login_required
def bulk_task_action(request):
    """
    Ejecutar acciones masivas en tareas
    """
    if request.method != 'POST':
        return redirect('panel:task-list')
    
    action = request.POST.get('action')
    task_ids = request.POST.getlist('task_ids')
    
    if not action or not task_ids:
        messages.warning(request, 'Debe seleccionar una acción y al menos una tarea.')
        return redirect('panel:task-list')
    
    tasks = Task.objects.filter(
        pk__in=task_ids,
        user=request.user
    )
    
    count = tasks.count()
    
    if action == 'delete':
        # Cancelar tareas en Celery antes de eliminar
        for task in tasks:
            if task.celery_task_id and task.status in ['PENDING', 'PROGRESS']:
                from apps.core.celery import app
                app.control.revoke(task.celery_task_id, terminate=True)
        
        tasks.delete()
        messages.success(request, f'{count} tareas eliminadas.')
    
    elif action == 'cancel':
        pending_tasks = tasks.filter(status__in=['PENDING', 'PROGRESS'])
        
        for task in pending_tasks:
            if task.celery_task_id:
                from apps.core.celery import app
                app.control.revoke(task.celery_task_id, terminate=True)
            
            task.status = 'CANCELLED'
            task.completed_at = timezone.now()
            task.save()
        
        messages.success(request, f'{pending_tasks.count()} tareas canceladas.')
    
    elif action == 'retry':
        failed_tasks = tasks.filter(status='FAILURE')
        
        for task in failed_tasks:
            # Crear nueva tarea de reintento
            new_task = Task.objects.create(
                user=task.user,
                name=f"{task.name} (Reintento)",
                description=task.description,
                task_type=task.task_type,
                status='PENDING',
                retry_of=task
            )
            
            # Aquí iría la lógica para reiniciar cada tipo de tarea
            # según task.task_type
        
        messages.success(request, f'{failed_tasks.count()} tareas reiniciadas.')
    
    return redirect('panel:task-list')


# =====================================================================
# =====================================================================
#                    SECCIÓN 5: LIMPIEZA Y MANTENIMIENTO
# =====================================================================
# =====================================================================

@login_required
def cleanup_tasks(request):
    """
    Limpiar tareas antiguas
    """
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('panel:task-list')
    
    if request.method == 'POST':
        days = int(request.POST.get('days', 30))
        
        # Ejecutar tarea de limpieza
        result = cleanup_old_tasks.delay(days)
        
        # Crear registro de tarea
        task = Task.objects.create(
            user=request.user,
            name=f"Limpieza de tareas antiguas ({days} días)",
            description=f"Eliminando tareas completadas hace más de {days} días",
            task_type='cleanup',
            celery_task_id=result.id,
            status='PENDING'
        )
        
        messages.success(request, 'Proceso de limpieza iniciado.')
        return redirect('panel:task-detail', pk=task.pk)
    
    # Mostrar formulario de confirmación
    context = {
        'old_tasks_count': Task.objects.filter(
            completed_at__lt=timezone.now() - timedelta(days=30),
            status__in=['SUCCESS', 'FAILURE', 'CANCELLED']
        ).count()
    }
    
    return render(request, 'panel/tasks/cleanup.html', context)


# =====================================================================
# =====================================================================
#                    SECCIÓN 6: API Y ESTADÍSTICAS
# =====================================================================
# =====================================================================

@login_required
def task_stats_api(request):
    """
    API para obtener estadísticas de tareas
    """
    # Período de tiempo
    period = request.GET.get('period', '7')  # días
    try:
        period_days = int(period)
    except:
        period_days = 7
    
    start_date = timezone.now() - timedelta(days=period_days)
    
    # Estadísticas generales
    tasks = Task.objects.filter(
        user=request.user,
        created_at__gte=start_date
    )
    
    stats = {
        'period': period_days,
        'total': tasks.count(),
        'by_status': {
            'pending': tasks.filter(status='PENDING').count(),
            'progress': tasks.filter(status='PROGRESS').count(),
            'success': tasks.filter(status='SUCCESS').count(),
            'failure': tasks.filter(status='FAILURE').count(),
            'cancelled': tasks.filter(status='CANCELLED').count(),
        },
        'by_type': {}
    }
    
    # Estadísticas por tipo
    type_counts = tasks.values('task_type').annotate(count=Count('id'))
    for item in type_counts:
        stats['by_type'][item['task_type']] = item['count']
    
    # Tareas por día
    daily_tasks = []
    for i in range(period_days):
        date = start_date + timedelta(days=i)
        count = tasks.filter(
            created_at__date=date.date()
        ).count()
        daily_tasks.append({
            'date': date.date().isoformat(),
            'count': count
        })
    
    stats['daily'] = daily_tasks
    
    # Tiempo promedio de ejecución
    completed_tasks = tasks.filter(
        status='SUCCESS',
        started_at__isnull=False,
        completed_at__isnull=False
    )
    
    if completed_tasks.exists():
        total_duration = timedelta()
        for task in completed_tasks:
            total_duration += (task.completed_at - task.started_at)
        
        avg_duration = total_duration / completed_tasks.count()
        stats['avg_duration'] = avg_duration.total_seconds()
    else:
        stats['avg_duration'] = 0
    
    return JsonResponse(stats)


@login_required
def export_tasks(request):
    """
    Exportar tareas a Excel
    """
    if request.method == 'POST':
        # Filtros
        status = request.POST.get('status')
        task_type = request.POST.get('type')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        
        # Construir queryset
        tasks = Task.objects.filter(user=request.user)
        
        if status:
            tasks = tasks.filter(status=status)
        if task_type:
            tasks = tasks.filter(task_type=task_type)
        if date_from:
            tasks = tasks.filter(created_at__gte=date_from)
        if date_to:
            tasks = tasks.filter(created_at__lte=date_to)
        
        # Generar Excel
        import openpyxl
        from django.http import HttpResponse
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Tareas'
        
        # Encabezados
        headers = ['ID', 'Nombre', 'Tipo', 'Estado', 'Creada', 'Iniciada', 'Completada', 'Duración', 'Resultado', 'Error']
        ws.append(headers)
        
        # Datos
        for task in tasks:
            duration = ''
            if task.started_at and task.completed_at:
                duration = str(task.completed_at - task.started_at)
            
            ws.append([
                task.id,
                task.name,
                task.task_type,
                task.status,
                task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '',
                task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else '',
                task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else '',
                duration,
                task.result[:100] if task.result else '',
                task.error[:100] if task.error else '',
            ])
        
        # Respuesta
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=tareas_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        wb.save(response)
        return response
    
    # Mostrar formulario
    return render(request, 'panel/tasks/export.html')


# =====================================================================
# =====================================================================
#                    SECCIÓN 7: MONITOREO EN TIEMPO REAL
# =====================================================================
# =====================================================================

class TaskMonitorView(LoginRequiredMixin, View):
    """
    Vista para monitorear tareas en tiempo real
    """
    template_name = 'panel/tasks/monitor.html'
    
    def get(self, request):
        """
        Mostrar dashboard de monitoreo
        """
        # Tareas activas
        active_tasks = Task.objects.filter(
            user=request.user,
            status__in=['PENDING', 'PROGRESS']
        ).order_by('-created_at')[:10]
        
        # Tareas recientes
        recent_tasks = Task.objects.filter(
            user=request.user
        ).order_by('-created_at')[:20]
        
        context = {
            'active_tasks': active_tasks,
            'recent_tasks': recent_tasks,
        }
        
        return render(request, self.template_name, context)


@login_required
def task_updates_stream(request):
    """
    Stream de actualizaciones de tareas (Server-Sent Events)
    """
    def event_stream():
        """
        Generador de eventos
        """
        while True:
            # Obtener tareas activas del usuario
            active_tasks = Task.objects.filter(
                user=request.user,
                status__in=['PENDING', 'PROGRESS']
            )
            
            updates = []
            
            for task in active_tasks:
                if task.celery_task_id:
                    result = AsyncResult(task.celery_task_id)
                    
                    # Detectar cambios de estado
                    old_status = task.status
                    
                    if result.state == 'SUCCESS' and task.status != 'SUCCESS':
                        task.status = 'SUCCESS'
                        task.result = str(result.result)
                        task.completed_at = timezone.now()
                        task.save()
                        
                        updates.append({
                            'id': task.id,
                            'status': 'SUCCESS',
                            'message': f'Tarea "{task.name}" completada'
                        })
                    
                    elif result.state == 'FAILURE' and task.status != 'FAILURE':
                        task.status = 'FAILURE'
                        task.error = str(result.info)
                        task.completed_at = timezone.now()
                        task.save()
                        
                        updates.append({
                            'id': task.id,
                            'status': 'FAILURE',
                            'message': f'Tarea "{task.name}" falló'
                        })
                    
                    elif result.state == 'PROGRESS':
                        if isinstance(result.info, dict):
                            progress = result.info.get('current', 0)
                            total = result.info.get('total', 100)
                            
                            if task.progress != progress:
                                task.status = 'PROGRESS'
                                task.progress = progress
                                task.progress_total = total
                                task.save()
                                
                                updates.append({
                                    'id': task.id,
                                    'status': 'PROGRESS',
                                    'progress': progress,
                                    'total': total,
                                    'message': f'Tarea "{task.name}": {progress}/{total}'
                                })
            
            # Enviar actualizaciones si hay cambios
            if updates:
                data = json.dumps(updates)
                yield f"data: {data}\n\n"
            
            # Esperar antes de verificar de nuevo
            import time
            time.sleep(2)
    
    response = HttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    
    return response