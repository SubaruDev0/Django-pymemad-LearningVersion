from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from apps.accounts import account_views

app_name = 'accounts'

urlpatterns = [
    # Login/Logout
    path('login/', account_views.CustomLoginView.as_view(), name='login'),
    path('logout/', account_views.LogoutView.as_view(), name='logout'),
    # path('signup/', account_views.SignUpView.as_view(), name='signup'),

    # # Password reset
    # path('password-reset/',
    #      auth_views.PasswordResetView.as_view(
    #          template_name='accounts/password_reset.html',
    #          email_template_name='accounts/password_reset_email.html',
    #          success_url=reverse_lazy('accounts:password_reset_done')
    #      ),
    #      name='password_reset'),
    
    # path('password-reset/done/',
    #      auth_views.PasswordResetDoneView.as_view(
    #          template_name='accounts/password_reset_done.html'
    #      ),
    #      name='password_reset_done'),
    
    # path('reset/<uidb64>/<token>/',
    #      auth_views.PasswordResetConfirmView.as_view(
    #          template_name='accounts/password_reset_confirm.html',
    #          success_url=reverse_lazy('accounts:password_reset_complete')
    #      ),
    #      name='password_reset_confirm'),
    
    # path('reset/done/',
    #      auth_views.PasswordResetCompleteView.as_view(
    #          template_name='accounts/password_reset_complete.html'
    #      ),
    #      name='password_reset_complete'),
    
    # # Profile
    # path('profile/', account_views.ProfileView.as_view(), name='profile'),
]
