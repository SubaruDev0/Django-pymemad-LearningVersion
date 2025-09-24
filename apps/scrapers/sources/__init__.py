from .canal9 import Canal9Scraper
from .biobio import BioBioScraper
from .diarioconcepcion import DiarioConcepcionScraper
from .emol import EmolScraper
from .gore import GoreScraper
from .minagri import MinagriScraper
from .infor import InforScraper
from .corma import CormaScraper
from .latribuna import LatribunaScraper
from .tvu import TvuScraper
from .soychile import SoyChileScraper
from .senado import SenadoScraper

SCRAPERS = {
    'canal9': Canal9Scraper,
    'biobio': BioBioScraper,
    'diarioconcepcion': DiarioConcepcionScraper,
    'emol': EmolScraper,
    'gore': GoreScraper,
    'minagri': MinagriScraper,
    'infor': InforScraper,
    'corma': CormaScraper,
    'latribuna': LatribunaScraper,
    'tvu': TvuScraper,
    'soychile': SoyChileScraper,
    'senado': SenadoScraper,
}

def get_scraper(source_name):
    scraper_class = SCRAPERS.get(source_name.lower())
    if scraper_class:
        return scraper_class()
    raise ValueError(f"Scraper no encontrado para {source_name}")
