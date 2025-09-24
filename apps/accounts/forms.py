# accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

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

        # Si es un email, buscar el usuario por email
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                pass

        # Si no, asumir que es username o RUT
        return username
