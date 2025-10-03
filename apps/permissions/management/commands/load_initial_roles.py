from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from apps.permissions.models import Role
from apps.core.models import PymeMadRegion


class Command(BaseCommand):
    help = 'Carga los roles iniciales del sistema PyMEMAD'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Cargando roles iniciales del sistema PyMEMAD...'))

        # Definir roles base del sistema
        roles_data = [
            # ========== ROL DE SISTEMA ==========
            {
                'code': 'super_admin',
                'name': 'Super Administrador',
                'description': 'Control total del sistema con acceso a todas las funcionalidades',
                'level': 'super_admin',
                'governance': 'national',
                'is_system': True,
                'is_active': True,
                'regions': [],  # Acceso a todas las regiones
            },

            # ========== ROLES NACIONALES ==========
            {
                'code': 'presidente_nacional',
                'name': 'Presidente Nacional',
                'description': 'Presidente con acceso total a nivel nacional',
                'level': 'national_president',
                'governance': 'national',
                'is_system': False,
                'is_active': True,
                'regions': [],  # Acceso a todas las regiones
            },
            {
                'code': 'tesorero_nacional',
                'name': 'Tesorero Nacional',
                'description': 'Tesorero nacional con acceso a finanzas de todas las regiones',
                'level': 'national_treasurer',
                'governance': 'national',
                'is_system': False,
                'is_active': True,
                'regions': [],
            },
            {
                'code': 'secretario_nacional',
                'name': 'Secretario Nacional',
                'description': 'Secretario nacional con acceso a documentación de todas las regiones',
                'level': 'national_secretary',
                'governance': 'national',
                'is_system': False,
                'is_active': True,
                'regions': [],
            },

            # ========== ROLES OPERATIVOS ==========
            {
                'code': 'administrativo',
                'name': 'Administrativo',
                'description': 'Personal administrativo con acceso operativo',
                'level': 'administrative',
                'governance': 'national',
                'is_system': False,
                'is_active': True,
                'regions': [],
            },
            {
                'code': 'contador',
                'name': 'Contador',
                'description': 'Contador con acceso a módulos financieros',
                'level': 'accountant',
                'governance': 'national',
                'is_system': False,
                'is_active': True,
                'regions': [],
            },
        ]

        # Obtener todas las regiones activas para crear roles regionales
        regions = PymeMadRegion.objects.filter(is_active=True)

        # Crear roles regionales dinámicamente para cada región
        regional_roles_templates = [
            {
                'code_prefix': 'presidente',
                'name_template': 'Presidente {region_name}',
                'description_template': 'Presidente regional de {region_name}',
                'level': 'regional_president',
            },
            {
                'code_prefix': 'tesorero',
                'name_template': 'Tesorero {region_name}',
                'description_template': 'Tesorero regional de {region_name}',
                'level': 'regional_treasurer',
            },
            {
                'code_prefix': 'secretario',
                'name_template': 'Secretario {region_name}',
                'description_template': 'Secretario regional de {region_name}',
                'level': 'regional_secretary',
            },
            {
                'code_prefix': 'socio',
                'name_template': 'Socio {region_name}',
                'description_template': 'Socio de la región {region_name} con acceso solo a su información',
                'level': 'active_member',
            },
        ]

        # Generar roles regionales
        for region in regions:
            region_code = region.code.lower().replace('_', '-')  # Convertir underscores a guiones
            for template in regional_roles_templates:
                roles_data.append({
                    'code': f"{template['code_prefix']}_pymemad_{region_code}",
                    'name': template['name_template'].format(region_name=region.name),
                    'description': template['description_template'].format(region_name=region.name),
                    'level': template['level'],
                    'governance': 'regional',
                    'is_system': False,
                    'is_active': True,
                    'regions': [region.id],
                })

        # Crear o actualizar roles
        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write('\n📋 Creando roles del sistema...\n')

        for role_data in roles_data:
            try:
                # Crear grupo Django si no existe
                group_name = role_data['name']
                django_group, _ = Group.objects.get_or_create(name=group_name)

                # Crear o actualizar rol
                role, created = Role.objects.update_or_create(
                    code=role_data['code'],
                    defaults={
                        'name': role_data['name'],
                        'description': role_data['description'],
                        'level': role_data['level'],
                        'governance': role_data['governance'],
                        'django_group': django_group,
                        'is_system': role_data.get('is_system', False),
                        'is_active': role_data.get('is_active', True),
                    }
                )

                # Asignar regiones si es rol regional
                if role_data['regions']:
                    role.allowed_regions.set(role_data['regions'])
                else:
                    role.allowed_regions.clear()

                if created:
                    created_count += 1
                    icon = '🔐' if role_data.get('is_system') else '👤'
                    self.stdout.write(f"  {icon} Creado: {role.name} ({role.code})")
                else:
                    updated_count += 1
                    self.stdout.write(f"  📝 Actualizado: {role.name} ({role.code})")

            except Exception as e:
                skipped_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error creando rol '{role_data['code']}': {e}")
                )

        # Resumen final
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado:'
                f'\n   - {created_count} roles creados'
                f'\n   - {updated_count} roles actualizados'
                f'\n   - {skipped_count} roles con errores'
            )
        )

        # Estadísticas
        total_roles = Role.objects.count()
        system_roles = Role.objects.filter(is_system=True).count()
        national_roles = Role.objects.filter(governance='national', is_system=False).count()
        regional_roles = Role.objects.filter(governance='regional').count()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n📊 Estadísticas:'
                f'\n   - Total de roles: {total_roles}'
                f'\n   - Roles de sistema: {system_roles}'
                f'\n   - Roles nacionales: {national_roles}'
                f'\n   - Roles regionales: {regional_roles}'
            )
        )

        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  PRÓXIMOS PASOS:'
                '\n   1. Ejecutar: python manage.py load_initial_modules (si aún no lo hiciste)'
                '\n   2. Asignar permisos a los roles desde el panel de administración'
                '\n   3. Asignar roles a los usuarios'
                '\n   4. Los permisos se configuran mediante RoleModuleAccess'
            )
        )
