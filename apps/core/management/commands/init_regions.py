from django.core.management.base import BaseCommand
from apps.core.models import PymeMadRegion
from apps.core.constants import REGION_CHOICES


class Command(BaseCommand):
    help = 'Inicializa las regiones de PyMEMAD'

    def handle(self, *args, **options):
        regions_data = [
            {
                'code': 'biobio-nuble',
                'name': 'Biobío-Ñuble',
                'rut': '65.123.456-7',
                'email': 'biobio-nuble@pymemad.cl',
                'phone': '+56 41 2123456',
                'address': 'Av. Libertad 123',
                'city': 'Concepción'
            },
            {
                'code': 'maule',
                'name': 'Maule',
                'rut': '65.234.567-8',
                'email': 'maule@pymemad.cl',
                'phone': '+56 71 2234567',
                'address': 'Calle Principal 456',
                'city': 'Talca'
            },
            {
                'code': 'araucania',
                'name': 'Araucanía',
                'rut': '65.345.678-9',
                'email': 'araucania@pymemad.cl',
                'phone': '+56 45 2345678',
                'address': 'Av. Alemania 789',
                'city': 'Temuco'
            },
            {
                'code': 'los-rios',
                'name': 'Los Ríos',
                'rut': '65.456.789-0',
                'email': 'los-rios@pymemad.cl',
                'phone': '+56 63 2456789',
                'address': 'Calle Valdivia 321',
                'city': 'Valdivia'
            }
        ]

        created_count = 0
        updated_count = 0

        for region_data in regions_data:
            region, created = PymeMadRegion.objects.update_or_create(
                code=region_data['code'],
                defaults={
                    'name': region_data['name'],
                    'rut': region_data['rut'],
                    'email': region_data['email'],
                    'phone': region_data['phone'],
                    'address': region_data['address'],
                    'city': region_data['city'],
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Región creada: {region.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'📝 Región actualizada: {region.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado: {created_count} regiones creadas, {updated_count} actualizadas'
            )
        )