# apps/accounts/account_views.py
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext as _, get_language
from django.views import View
from django.views.generic import FormView, TemplateView
from django.conf import settings
from .forms import Custompymemadm, CustomPasswordResetForm, CustomSetPasswordForm

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:dashboard')
        form = Custompymemadm()
        return render(request, 'signin.html', {'form': form})
    
    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if not username or not password:
            return JsonResponse({
                'success': False,
                'message': 'Por favor, complete todos los campos.'
            }, status=400)
        logger.info(f"Intento de login para usuario: {username}")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                logger.info(f"Login exitoso para usuario: {username}")
                next_url = request.GET.get('next') or request.POST.get('next')
                redirect_url = next_url or reverse('dashboard:dashboard')
                return JsonResponse({
                    'success': True,
                    'action': 'auto',
                    'redirect_url': redirect_url,
                    'message': _('Inicio de sesión exitoso. Redirigiendo...')
                })
            else:
                logger.warning(f"Intento de login con cuenta inactiva: {username}")
                return JsonResponse({
                    'success': False,
                    'message': _('Su cuenta está desactivada. Contacte al administrador del sistema.')
                }, status=400)
        else:
            logger.warning(f"Intento de login fallido para: {username}")
            return JsonResponse({
                'success': False,
                'message': _('Las credenciales ingresadas no son válidas. Verifique su usuario y contraseña.')
            }, status=400)

class PasswordResetView(FormView):
    template_name = 'password_reset.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('accounts:password_reset_done')
    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': default_token_generator,
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pymemad.cl'),
            'email_template_name': 'email/password_reset_email.html',
            'subject_template_name': 'email/password_reset_subject.txt',
            'request': self.request,
            'html_email_template_name': 'email/password_reset_email.html',
        }
        form.save(**opts)
        logger.info(f"Email de recuperación enviado a: {form.cleaned_data['email']}")
        return super().form_valid(form)

class PasswordResetDoneView(TemplateView):
    template_name = 'password_reset_done.html'

class PasswordResetConfirmView(FormView):
    template_name = 'password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('accounts:password_reset_complete')
    def dispatch(self, *args, **kwargs):
        self.validlink = False
        self.user = self.get_user(kwargs['uidb64'])
        if self.user is not None:
            token = kwargs['token']
            if token == 'set-password':
                session_token = self.request.session.get('_password_reset_token')
                if default_token_generator.check_token(self.user, session_token):
                    self.validlink = True
            else:
                if default_token_generator.check_token(self.user, token):
                    self.request.session['_password_reset_token'] = token
                    redirect_url = self.request.path.replace(token, 'set-password')
                    return redirect(redirect_url)
        return super().dispatch(*args, **kwargs)
    def get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, AttributeError):
            user = None
        return user
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['validlink'] = self.validlink
        return context
    def form_valid(self, form):
        user = form.save()
        from apps.accounts.tasks import send_password_reset_confirmation_email_task
        send_password_reset_confirmation_email_task.delay(user_id=user.id)
        del self.request.session['_password_reset_token']
        logger.info(f"Contraseña restablecida exitosamente para: {user.email}")
        return super().form_valid(form)

class PasswordResetCompleteView(TemplateView):
    template_name = 'password_reset_complete.html'

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('accounts:login')