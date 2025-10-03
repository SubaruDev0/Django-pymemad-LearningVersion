from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'permissions'

urlpatterns = [
    # Redirección de la raíz a roles
    path('', RedirectView.as_view(pattern_name='permissions:roles_management', permanent=False)),

    # Vista de usuarios y permisos
    path('users/', views.permissions_list, name='permissions_list'),

    # Detalle de permisos de usuario
    path('user/<int:user_id>/', views.user_permissions_detail, name='user_permissions_detail'),

    # Gestión de roles
    path('roles/', views.roles_management, name='roles_management'),
    path('role/<int:role_id>/configure/', views.configure_role_wizard, name='configure_role_wizard'),

    # Gestión de módulos
    path('modules/', views.modules_management, name='modules_management'),
    path('modules/create/', views.ModuleCreateView.as_view(), name='module_create'),
    path('modules/<int:pk>/edit/', views.ModuleUpdateView.as_view(), name='module_edit'),

    # AJAX endpoints
    path('assign-role/', views.assign_role, name='assign_role'),
    path('toggle-user-status/', views.toggle_user_status, name='toggle_user_status'),
    path('update-module-permissions/', views.update_module_permissions, name='update_module_permissions'),

    # Auditoría
    path('audit/', views.audit_logs, name='audit_logs'),

    # === API ENDPOINTS ===
    # Users API
    path('api/users/create/', views.api_create_user, name='api_create_user'),

    # Roles API
    path('api/roles/', views.api_create_role, name='api_create_role'),
    path('api/role/<int:role_id>/permissions/', views.api_get_role_permissions, name='api_get_role_permissions'),
    path('api/role/<int:role_id>/update-permissions/', views.api_update_role_permissions, name='api_update_role_permissions'),
    path('api/role/<int:role_id>/configure/', views.api_configure_role_wizard, name='api_configure_role_wizard'),
    path('api/role/<int:role_id>/configuration/', views.api_get_role_configuration, name='api_get_role_configuration'),
    path('api/role/<int:role_id>/', views.api_delete_role, name='api_delete_role'),
    path('api/role/<int:role_id>/users/', views.api_get_role_users, name='api_get_role_users'),
    path('api/user/<int:user_id>/remove-role/', views.api_remove_user_role, name='api_remove_user_role'),

    # Modules API
    path('api/modules/', views.api_modules_list, name='api_modules_list'),
    path('api/modules/create/', views.api_create_module, name='api_create_module'),
    path('api/module/<int:module_id>/', views.api_module_detail, name='api_module_detail'),
]
