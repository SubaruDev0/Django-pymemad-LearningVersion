from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

from apps.scrapers.sources import SCRAPERS, get_scraper

logger = logging.getLogger('scrapers')

class Command(BaseCommand):
    help = 'Ejecuta scrapers de noticias PYMEMAD'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Fuente específica a scrapear (ej: canal9, emol)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Ejecutar todos los scrapers',
        )
        
    def handle(self, *args, **options):
        sources_to_scrape = []
        
        if options['all']:
            sources_to_scrape = list(SCRAPERS.keys())
        elif options['source']:
            if options['source'].lower() in SCRAPERS:
                sources_to_scrape = [options['source'].lower()]
            else:
                self.stdout.write(
                    self.style.ERROR(f"Fuente '{options['source']}' no encontrada.")
                )
                self.stdout.write(f"Fuentes disponibles: {', '.join(SCRAPERS.keys())}")
                return
        else:
            self.stdout.write(self.style.ERROR("Debe especificar --source o --all"))
            return
        
        self.stdout.write(f"Iniciando scraping a las {timezone.now()}")
        
        for source in sources_to_scrape:
            try:
                self.stdout.write(f"\nProcesando {source}...")
                scraper = get_scraper(source)
                scraper.scrape()
                self.stdout.write(self.style.SUCCESS(f"✓ {source} completado"))
            except Exception as e:
                logger.error(f"Error en {source}: {e}")
                self.stdout.write(self.style.ERROR(f"✗ {source} falló: {e}"))
        
        self.stdout.write(self.style.SUCCESS("\nScraping completado"))
