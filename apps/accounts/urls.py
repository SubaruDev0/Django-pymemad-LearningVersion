# apps/accounts/urls.py
from django.urls import path, reverse_lazy
from apps.accounts import account_views
from apps.accounts import profile_views

app_name = 'accounts'
urlpatterns = [
    # ====== LOGIN / LOGOUT ======
    path('login/', account_views.CustomLoginView.as_view(), name='login'),
    path('logout/', account_views.LogoutView.as_view(), name='logout'),
    
    # ====== SISTEMA DE RECUPERACIÓN DE CONTRASEÑA ======
    path('password-reset/', account_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', account_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', account_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', account_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # ====== CAMBIO DE CONTRASEÑA (USUARIO AUTENTICADO) ======
    path('profile/password/change/', profile_views.PasswordChangeView.as_view(), name='password-change'),
    
    # ====== CONFIGURACIÓN DE PERFIL ======
    path('profile/settings/', profile_views.ProfileSettingsView.as_view(), name='profile-settings'),
    path('profile/update/', profile_views.ProfileUpdateView.as_view(), name='profile-update'),
    path('profile/avatar/update/', profile_views.AvatarUpdateView.as_view(), name='avatar-update'),
    path('profile/avatar/delete/', profile_views.AvatarDeleteView.as_view(), name='avatar-delete'),
]