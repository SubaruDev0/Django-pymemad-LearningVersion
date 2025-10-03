# apps/accounts/profile_forms.py *** ***
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):
    """
    Formulario para actualizar los datos del perfil del usuario
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese su nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese su apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+56 9 1234 5678'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Cuéntanos un poco sobre ti...'
            })
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
            'phone': 'Teléfono',
            'bio': 'Acerca de mí'
        }

    def clean_email(self):
        """
        Valida que el email no esté siendo usado por otro usuario
        """
        email = self.cleaned_data.get('email')
        if email:
            # Excluir el usuario actual de la validación
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return email


class AvatarUpdateForm(forms.ModelForm):
    """
    Formulario para actualizar la foto de perfil
    """
    class Meta:
        model = User
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'avatar': 'Foto de perfil'
        }

    def clean_avatar(self):
        """
        Valida el tamaño y tipo de archivo de la imagen
        """
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Validar tamaño (máximo 5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError('La imagen no debe superar los 5MB.')
            
            # Validar tipo de archivo
            valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if avatar.content_type not in valid_types:
                raise forms.ValidationError('Solo se permiten archivos de imagen (JPEG, PNG, GIF, WebP).')
        
        return avatar


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Formulario personalizado para cambiar contraseña con estilos Bootstrap
    """
    old_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña actual'
        })
    )
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su nueva contraseña'
        }),
        help_text="""
        <ul class="small text-muted ps-3">
            <li>Tu contraseña debe tener al menos 8 caracteres.</li>
            <li>No puede ser una contraseña común.</li>
            <li>No puede ser completamente numérica.</li>
            <li>No puede ser similar a tu información personal.</li>
        </ul>
        """
    )
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su nueva contraseña'
        })
    )


class DeleteAccountForm(forms.Form):
    """
    Formulario para confirmar la eliminación de la cuenta
    """
    password = forms.CharField(
        label="Confirme su contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña para confirmar'
        }),
        help_text="Por seguridad, debe confirmar su contraseña para eliminar su cuenta."
    )
    
    confirm = forms.BooleanField(
        label="Entiendo que esta acción es irreversible",
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )