from abc import ABC, abstractmethod
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from apps.news.models import News, NewsSource, ScrapingLog
from django.utils import timezone

class BaseScraper(ABC):
    def __init__(self, source_name):
        self.source_name = source_name
        self.source = self.get_or_create_source()
        self.logger = logging.getLogger(f'scrapers.{source_name}')
        self.driver = None
        self.scraping_log = None
        
    @abstractmethod
    def get_source_config(self):
        """
        Retorna diccionario con configuración de la fuente:
        {
            'base_url': 'https://...',
            'search_url': 'https://...',
            'requires_selenium': True/False
        }
        """
        pass
    
    def get_or_create_source(self):
        config = self.get_source_config()
        source, created = NewsSource.objects.get_or_create(
            name=self.source_name,
            defaults={'base_url': config['base_url']}
        )
        return source
    
    def setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Evitar detección de Selenium
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def cleanup_selenium(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    @abstractmethod
    def extract_news_list(self, html_content):
        """
        Extrae lista de noticias del HTML
        Retorna lista de diccionarios con al menos: title, url
        """
        pass
    
    @abstractmethod
    def extract_news_details(self, news_url):
        """
        Extrae detalles de una noticia específica
        Retorna diccionario con: content, excerpt, published_date, image_url, author
        """
        pass
    
    def save_news(self, news_data):
        """Guarda noticia en la base de datos"""
        try:
            news, created = News.objects.get_or_create(
                url=news_data['url'],
                defaults={
                    'source': self.source,
                    'title': news_data.get('title', ''),
                    'content': news_data.get('content', ''),
                    'excerpt': news_data.get('excerpt', ''),
                    'published_date': news_data.get('published_date'),
                    'image_url': news_data.get('image_url', ''),
                    'author': news_data.get('author', ''),
                }
            )
            return created
        except Exception as e:
            self.logger.error(f"Error guardando noticia: {e}")
            return False
    
    def scrape(self):
        """Método principal de scraping"""
        self.scraping_log = ScrapingLog.objects.create(source=self.source)
        
        try:
            config = self.get_source_config()
            
            if config.get('requires_selenium', False):
                self.setup_selenium()
            
            self.logger.info(f"Iniciando scraping de {self.source_name}")
            
            # Obtener lista de noticias
            if config.get('requires_selenium', False):
                self.driver.get(config['search_url'])
                html_content = self.driver.page_source
            else:
                response = requests.get(config['search_url'])
                html_content = response.text
            
            news_list = self.extract_news_list(html_content)
            self.scraping_log.news_found = len(news_list)
            
            # Procesar cada noticia
            news_saved = 0
            for news_item in news_list:
                try:
                    # Obtener detalles
                    details = self.extract_news_details(news_item['url'])
                    
                    # Combinar datos
                    news_data = {**news_item, **details}
                    
                    # Guardar
                    if self.save_news(news_data):
                        news_saved += 1
                        
                except Exception as e:
                    self.logger.error(f"Error procesando noticia {news_item.get('url', '')}: {e}")
            
            self.scraping_log.news_saved = news_saved
            self.scraping_log.status = 'completed'
            self.logger.info(f"Scraping completado: {news_saved}/{len(news_list)} noticias guardadas")
            
        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")
            self.scraping_log.status = 'failed'
            self.scraping_log.error_message = str(e)
            
        finally:
            self.scraping_log.finished_at = timezone.now()
            self.scraping_log.save()
            
            if config.get('requires_selenium', False):
                self.cleanup_selenium()