from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('ready/', views.readiness_check, name='readiness_check'),
]