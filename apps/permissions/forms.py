"""
Formularios para el sistema de permisos de PyMEMAD
"""
from django import forms
from django.contrib.auth import get_user_model
from apps.permissions.models import Module, Role, RoleModuleAccess

User = get_user_model()


class ModuleForm(forms.ModelForm):
    """Formulario para crear/editar módulos"""

    # Campo para seleccionar las acciones disponibles
    available_actions = forms.MultipleChoiceField(
        choices=Module.ACTION_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label='Acciones Disponibles',
        help_text='Seleccione las acciones que estarán disponibles para este módulo'
    )

    class Meta:
        model = Module
        fields = [
            'code', 'name', 'app_label', 'description',
            'icon', 'url_namespace', 'available_actions',
            'order', 'is_active', 'parent'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: members'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Miembros'
            }),
            'app_label': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: members'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del módulo...'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: fas fa-users'
            }),
            'url_namespace': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: members'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si estamos editando, cargar las acciones seleccionadas
        if self.instance.pk and self.instance.available_actions:
            self.initial['available_actions'] = self.instance.available_actions
        else:
            # Por defecto, CRUD básico
            self.initial['available_actions'] = ['view', 'add', 'change', 'delete']

        # Excluir el módulo actual de la lista de padres posibles
        if self.instance.pk:
            self.fields['parent'].queryset = Module.objects.exclude(
                pk=self.instance.pk
            ).filter(is_active=True)
        else:
            self.fields['parent'].queryset = Module.objects.filter(is_active=True)

        # Hacer opcional el parent
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = "-- Sin módulo padre (nivel superior) --"

    def clean_available_actions(self):
        """Convierte la lista de selección múltiple a JSON"""
        actions = self.cleaned_data.get('available_actions', [])
        if not actions:
            # Si no se selecciona nada, usar CRUD básico
            actions = ['view', 'add', 'change', 'delete']
        return list(actions)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Las acciones ya vienen como lista desde clean_available_actions
        if commit:
            instance.save()
        return instance


class RoleModuleAccessForm(forms.ModelForm):
    """Formulario para configurar acceso de rol a módulo"""

    enabled_actions = forms.MultipleChoiceField(
        choices=[],  # Se llena dinámicamente
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label='Permisos Habilitados'
    )

    class Meta:
        model = RoleModuleAccess
        fields = ['enabled_actions', 'settings']
        widgets = {
            'settings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"max_export_rows": 1000, "allow_bulk_operations": true}'
            })
        }

    def __init__(self, *args, **kwargs):
        # Obtener el módulo del contexto
        self.module = kwargs.pop('module', None)
        self.role = kwargs.pop('role', None)

        super().__init__(*args, **kwargs)

        # Configurar las opciones de acciones basadas en el módulo
        if self.module:
            available_actions = self.module.get_available_actions()
            action_choices = [
                (action, self.module.get_action_display(action))
                for action in available_actions
            ]
            self.fields['enabled_actions'].choices = action_choices

        # Si estamos editando, cargar las acciones habilitadas
        if self.instance.pk and self.instance.enabled_actions:
            self.initial['enabled_actions'] = self.instance.enabled_actions

    def clean_enabled_actions(self):
        """Convierte la selección múltiple a lista"""
        return list(self.cleaned_data.get('enabled_actions', []))

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Asegurar que tenemos role y module
        if self.role and not instance.role_id:
            instance.role = self.role
        if self.module and not instance.module_id:
            instance.module = self.module

        if commit:
            instance.save()

        return instance


class RolePermissionsForm(forms.ModelForm):
    """Formulario para configurar permisos de un rol"""

    class Meta:
        model = Role
        fields = ['permissions_json']
        widgets = {
            'permissions_json': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Inicializar con estructura vacía si no existe
        if not self.instance.permissions_json:
            self.instance.permissions_json = {
                'modules': {},
                'special_permissions': {},
                'restrictions': {}
            }


class UserRoleAssignmentForm(forms.Form):
    """Formulario para asignar roles a usuarios"""

    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Seleccione un usuario'
        }),
        label='Usuario'
    )

    primary_role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Rol Principal',
        required=False,
        empty_label='-- Sin rol --'
    )

    additional_roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Roles Adicionales',
        required=False
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notas sobre la asignación (opcional)'
        }),
        label='Notas',
        required=False
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Ordenar usuarios por nombre
        self.fields['user'].queryset = User.objects.all().order_by('first_name', 'last_name', 'username')

        # Ordenar roles por nivel y nombre
        self.fields['primary_role'].queryset = Role.objects.filter(is_active=True).order_by('level', 'name')
        self.fields['additional_roles'].queryset = Role.objects.filter(is_active=True).order_by('level', 'name')

        if user:
            self.fields['user'].initial = user
            self.fields['user'].widget.attrs['readonly'] = True
            self.fields['primary_role'].initial = user.primary_role
            self.fields['additional_roles'].initial = user.additional_roles.all()

    def save(self):
        user = self.cleaned_data['user']
        user.primary_role = self.cleaned_data.get('primary_role')
        user.save()

        # Actualizar roles adicionales
        user.additional_roles.clear()
        for role in self.cleaned_data.get('additional_roles', []):
            user.additional_roles.add(role)

        return user


class BulkRoleAssignmentForm(forms.Form):
    """Formulario para asignar rol a múltiples usuarios"""

    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Usuarios'
    )

    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Rol a Asignar'
    )

    assignment_type = forms.ChoiceField(
        choices=[
            ('primary', 'Como Rol Principal'),
            ('additional', 'Como Rol Adicional')
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='Tipo de Asignación',
        initial='primary'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ordenar usuarios y roles
        self.fields['users'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        self.fields['role'].queryset = Role.objects.filter(
            is_active=True
        ).order_by('level', 'name')

    def save(self):
        users = self.cleaned_data['users']
        role = self.cleaned_data['role']
        assignment_type = self.cleaned_data['assignment_type']

        updated_users = []

        for user in users:
            if assignment_type == 'primary':
                user.primary_role = role
                user.save()
            else:
                user.additional_roles.add(role)

            updated_users.append(user)

        return updated_users


class RoleCreationForm(forms.ModelForm):
    """Formulario para crear roles"""

    class Meta:
        model = Role
        fields = ['code', 'name', 'description', 'level']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: regional_coordinator',
                'pattern': '^[a-z0-9_]+$',
                'title': 'Solo minúsculas, números y guión bajo'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Coordinador Regional'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del rol y sus responsabilidades...'
            }),
            'level': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            # Validar que solo contenga minúsculas, números y guión bajo
            import re
            if not re.match(r'^[a-z0-9_]+$', code):
                raise forms.ValidationError(
                    'El código solo puede contener minúsculas, números y guión bajo'
                )
        return code


class ModuleActionConfigForm(forms.Form):
    """Formulario para configurar acciones de un módulo"""

    def __init__(self, module, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Obtener todas las acciones posibles
        from .constants import STANDARD_ACTIONS, get_actions_by_category

        actions_by_category = get_actions_by_category()

        # Crear campos dinámicamente por categoría
        for category_name, actions in actions_by_category.items():
            for action_code, action_name, action_description in actions:
                field_name = f'action_{action_code}'
                initial_value = action_code in (module.available_actions or [])

                self.fields[field_name] = forms.BooleanField(
                    label=action_name,
                    help_text=action_description,
                    required=False,
                    initial=initial_value,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input',
                        'data-category': category_name,
                        'data-action': action_code
                    })
                )

    def get_selected_actions(self):
        """Obtiene las acciones seleccionadas"""
        selected = []
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('action_') and value:
                action_code = field_name.replace('action_', '')
                selected.append(action_code)
        return selected


class PermissionSearchForm(forms.Form):
    """Formulario para buscar permisos"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por usuario, rol o módulo...'
        })
    )

    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        required=False,
        empty_label='-- Todos los roles --',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    module = forms.ModelChoiceField(
        queryset=Module.objects.filter(is_active=True),
        required=False,
        empty_label='-- Todos los módulos --',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    status = forms.ChoiceField(
        choices=[
            ('', '-- Todos --'),
            ('active', 'Activos'),
            ('inactive', 'Inactivos')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )