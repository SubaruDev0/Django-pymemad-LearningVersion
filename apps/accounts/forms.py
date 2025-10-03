# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm as BasePasswordResetForm,
    SetPasswordForm as BaseSetPasswordForm,
    PasswordChangeForm as BasePasswordChangeForm
)
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files.uploadedfile import UploadedFile

User = get_user_model()


class Custompymemadm(AuthenticationForm):
    """Formulario personalizado de login que acepta email o RUT"""
    username = forms.CharField(
        label=_('Email o RUT'),
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('correo@empresa.cl o RUT')
        })
    )
    password = forms.CharField(
        label=_('Contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Ingresa tu contraseña')
        })
    )

    def clean_username(self):
        """Permite login con email o RUT"""
        username = self.cleaned_data.get('username')
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                pass
        return username


class CustomPasswordResetForm(BasePasswordResetForm):
    """Formulario personalizado para solicitar recuperación de contraseña"""
    email = forms.EmailField(
        label=_('Correo electrónico'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Ingresa tu correo electrónico'),
            'autocomplete': 'email'
        })
    )

    def clean_email(self):
        """Valida que el email exista y esté activo"""
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError(_('No existe una cuenta activa con este correo electrónico.'))
        return email

    def save(self, domain_override=None, subject_template_name='email/password_reset_subject.txt',
             email_template_name='email/password_reset_email.html', use_https=False,
             token_generator=None, from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """Sobrescribe para usar Celery"""
        from apps.accounts.tasks import send_password_reset_email_task
        email = self.cleaned_data["email"]
        if not domain_override:
            domain = request.get_host() if request else 'pymemad.cl'
        else:
            domain = domain_override
        for user in User.objects.filter(email=email, is_active=True):
            send_password_reset_email_task.delay(
                user_id=user.id,
                domain=domain,
                use_https=use_https or (request and request.is_secure())
            )


class CustomSetPasswordForm(BaseSetPasswordForm):
    """Formulario para establecer nueva contraseña tras recuperación"""
    new_password1 = forms.CharField(
        label=_('Nueva contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Ingresa tu nueva contraseña'),
            'autocomplete': 'new-password'
        }),
        help_text=_('La contraseña debe tener al menos 8 caracteres.')
    )
    new_password2 = forms.CharField(
        label=_('Confirmar nueva contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Confirma tu nueva contraseña'),
            'autocomplete': 'new-password'
        })
    )


class CustomPasswordChangeForm(BasePasswordChangeForm):
    """Formulario para cambiar contraseña desde el perfil (usuario autenticado)"""
    old_password = forms.CharField(
        label=_('Contraseña actual'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Ingresa tu contraseña actual'),
            'autocomplete': 'current-password'
        })
    )
    new_password1 = forms.CharField(
        label=_('Nueva contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Ingresa tu nueva contraseña'),
            'autocomplete': 'new-password'
        }),
        help_text=_('La contraseña debe tener al menos 8 caracteres.')
    )
    new_password2 = forms.CharField(
        label=_('Confirmar nueva contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg ps-5',
            'placeholder': _('Confirma tu nueva contraseña'),
            'autocomplete': 'new-password'
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    """Formulario para actualizar datos básicos del perfil"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg ps-5',
                'placeholder': _('Tu nombre'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg ps-5',
                'placeholder': _('Tu apellido'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg ps-5',
                'placeholder': _('correo@empresa.cl'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-lg ps-5',
                'placeholder': _('+56 9 1234 5678'),
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control form-control-lg ps-5',
                'placeholder': _('Cuéntanos sobre ti...'),
                'rows': 4,
            }),
        }
        labels = {
            'first_name': _('Nombre'),
            'last_name': _('Apellido'),
            'email': _('Correo electrónico'),
            'phone': _('Teléfono'),
            'bio': _('Biografía'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        """Valida que el email sea único (excluyendo al usuario actual)"""
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise ValidationError(_('Ya existe una cuenta con este correo electrónico.'))
        return email


class AvatarUpdateForm(forms.ModelForm):
    """Formulario para actualizar la foto de perfil"""
    class Meta:
        model = User
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
        labels = {
            'avatar': _('Foto de perfil'),
        }

    def clean_avatar(self):
        """Valida el tamaño y tipo de archivo del avatar"""
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if isinstance(avatar, UploadedFile):
                # Validar tamaño (máximo 5MB)
                if avatar.size > 5 * 1024 * 1024:
                    raise ValidationError(_('El archivo no puede superar los 5 MB.'))
                
                # Validar tipo de archivo
                allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if avatar.content_type not in allowed_types:
                    raise ValidationError(_('Solo se permiten archivos JPEG, PNG, GIF o WebP.'))
        return avatar