from django.urls import path
from . import views
from .error_views import permission_denied_view, page_not_found_view, server_error_view

app_name = 'core'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('ready/', views.readiness_check, name='readiness_check'),

    # Test error pages (solo para desarrollo)
    path('test-403/', permission_denied_view, name='test_403'),
    path('test-404/', page_not_found_view, name='test_404'),
    path('test-500/', server_error_view, name='test_500'),
]