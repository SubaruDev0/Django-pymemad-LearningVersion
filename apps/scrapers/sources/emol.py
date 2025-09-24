from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class EmolScraper(BaseScraper):
    def __init__(self):
        super().__init__('Emol')
        
    def get_source_config(self):
        return {
            'base_url': 'https://www.emol.com',
            'search_url': 'https://www.emol.com/buscador/?query=pymemad',
            'requires_selenium': True
        }
    
    def extract_news_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []
        
        try:
            if self.driver:
                wait = WebDriverWait(self.driver, 30)
                
                # Esperar que cargue la página
                self.logger.info("Esperando que carguen los resultados...")
                time.sleep(5)
                
                # Procesar múltiples páginas
                max_paginas = 3
                pagina_actual = 1
                
                while pagina_actual <= max_paginas:
                    self.logger.info(f"Procesando página {pagina_actual}...")
                    
                    # Esperar que cargue la lista de noticias
                    try:
                        wait.until(EC.presence_of_element_located((By.ID, "listNews")))
                    except:
                        self.logger.warning("No se encontró la lista de noticias")
                        break
                    
                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Buscar la lista de noticias
                    list_news = soup.find('ul', id='listNews')
                    
                    if not list_news:
                        # Buscar alternativa
                        list_news = soup.find('div', class_='bus_noticias')
                        if list_news:
                            list_news = list_news.find('ul')
                    
                    if not list_news:
                        self.logger.warning("No se encontró la lista de noticias")
                        break
                    
                    # Buscar todos los items de noticias
                    items = list_news.find_all('li', id='ContenedorLinkNoticia')
                    self.logger.info(f"Encontrados {len(items)} items de noticias")
                    
                    for item in items:
                        noticia = self.extraer_datos_noticia(item)
                        if noticia:
                            news_list.append(noticia)
                            self.logger.info(f"Noticia encontrada: {noticia['title'][:60]}...")
                    
                    # Intentar ir a la siguiente página
                    if pagina_actual < max_paginas:
                        if not self.navegar_siguiente_pagina(pagina_actual):
                            self.logger.info("No hay más páginas disponibles")
                            break
                        
                        pagina_actual += 1
                        time.sleep(3)
                    else:
                        break
                        
        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")
            
        return news_list
    
    def extraer_datos_noticia(self, item):
        """Extraer datos de una noticia específica de Emol"""
        try:
            # Buscar el enlace principal
            link_elem = item.find('a', id='LinkNoticia')
            if not link_elem:
                return None
            
            titulo = link_elem.get_text().strip()
            url = link_elem.get('href', '')
            
            # Limpiar y completar URL
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith('http'):
                url = urljoin(self.get_source_config()['base_url'], url)
            
            # Solo devolver si tiene título y URL válidos
            if titulo and url:
                return {
                    'title': titulo,
                    'url': url
                }
                
        except Exception as e:
            self.logger.error(f"Error extrayendo noticia: {e}")
            
        return None
    
    def navegar_siguiente_pagina(self, pagina_actual):
        """Navegar a la siguiente página de resultados"""
        try:
            # Emol usa JavaScript para la paginación
            # Buscar el enlace "Siguiente"
            next_link = self.driver.find_element(By.ID, "li_next")
            if next_link and next_link.is_displayed():
                # Buscar el enlace dentro
                link = next_link.find_element(By.TAG_NAME, "a")
                if link:
                    self.logger.info("Navegando a siguiente página")
                    self.driver.execute_script("arguments[0].click();", link)
                    time.sleep(3)
                    return True
            
            # Alternativa: buscar por número de página
            try:
                page_links = self.driver.find_elements(By.CSS_SELECTOR, "#listPages a")
                for link in page_links:
                    if link.get_text().strip() == str(pagina_actual + 1):
                        self.logger.info(f"Navegando a página {pagina_actual + 1}")
                        self.driver.execute_script("arguments[0].click();", link)
                        time.sleep(3)
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self.logger.debug(f"No se pudo navegar a la siguiente página: {e}")
            return False
    
    def extract_news_details(self, news_url):
        details = {
            'content': '',
            'excerpt': '',
            'published_date': None,
            'image_url': '',
            'author': ''
        }
        
        try:
            # Manejar URLs especiales de Emol
            if 'digital.elmercurio.com' in news_url:
                self.logger.info("Noticia de El Mercurio Digital - Contenido puede requerir suscripción")
                details['content'] = "[Contenido de El Mercurio Digital - Puede requerir suscripción]"
                details['excerpt'] = "Contenido de El Mercurio Digital"
                return details
            
            if self.driver:
                self.driver.get(news_url)
                time.sleep(4)
                html = self.driver.page_source
            else:
                import requests
                response = requests.get(news_url)
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar contenido principal
            contenido = ""
            
            # Selectores específicos para Emol
            contenido_selectores = [
                '#contenidos',
                '.EmolText',
                '.contenido',
                '#texto',
                'div[itemprop="articleBody"]',
                '.detail__content',
                '.article-body'
            ]
            
            for selector in contenido_selectores:
                elemento = soup.select_one(selector)
                if elemento:
                    # Limpiar elementos no deseados
                    for unwanted in elemento.find_all(['script', 'style', '.ad', '.banner', 'iframe']):
                        unwanted.decompose()
                    
                    # Buscar párrafos
                    paragrafos = elemento.find_all('p')
                    if paragrafos:
                        contenido_parrafos = []
                        for p in paragrafos:
                            texto = p.get_text().strip()
                            if texto and len(texto) > 20:
                                contenido_parrafos.append(texto)
                        
                        if contenido_parrafos:
                            contenido = '\n\n'.join(contenido_parrafos)
                            break
            
            # Si no se encuentra contenido estructurado
            if not contenido or len(contenido) < 100:
                # Buscar en el cuerpo principal
                main_content = soup.find('div', class_=re.compile(r'cont.*nota'))
                if main_content:
                    paragrafos = main_content.find_all('p')
                    contenido = '\n\n'.join([p.get_text().strip() for p in paragrafos[:20] if p.get_text().strip()])
            
            if contenido:
                details['content'] = contenido[:5000]
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido
            
            # Buscar fecha
            # Primero buscar en el span con clase bus_txt_fuente del item original
            fecha_selectores = [
                '.fecha',
                '.date',
                'time[datetime]',
                '.article-date',
                '[class*="fecha"]'
            ]
            
            for selector in fecha_selectores:
                fecha_elem = soup.select_one(selector)
                if fecha_elem:
                    fecha_texto = ""
                    if fecha_elem.get('datetime'):
                        fecha_texto = fecha_elem.get('datetime')
                    else:
                        fecha_texto = fecha_elem.get_text().strip()
                    
                    if fecha_texto:
                        fecha_normalizada = self.normalizar_fecha_emol(fecha_texto)
                        if fecha_normalizada:
                            details['published_date'] = fecha_normalizada
                            break
            
            # Buscar imagen
            img_selectores = [
                'img[src*="emol"]',
                '.imagen-noticia img',
                '.article-image img',
                'img[itemprop="image"]'
            ]
            
            for selector in img_selectores:
                img_elem = soup.select_one(selector)
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src', '')
                    # Manejar lazy loading
                    if not src or src == '#':
                        src = img_elem.get('data-original', '')
                    
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif not src.startswith('http'):
                        src = urljoin(news_url, src)
                    
                    details['image_url'] = src
                    break
            
            # Buscar autor/fuente
            autor_selectores = [
                '.autor',
                '.author',
                '.fuente',
                '[class*="autor"]'
            ]
            
            for selector in autor_selectores:
                autor_elem = soup.select_one(selector)
                if autor_elem:
                    details['author'] = autor_elem.get_text().strip()
                    break
                    
        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")
        
        return details
    
    def normalizar_fecha_emol(self, fecha_texto):
        """Normalizar formato de fecha de Emol"""
        try:
            # Emol usa formato: "DD/MM/YYYY"
            if '/' in fecha_texto:
                partes = fecha_texto.split('/')
                if len(partes) == 3:
                    dia = int(partes[0])
                    mes = int(partes[1])
                    año = int(partes[2])
                    return datetime(año, mes, dia)
            
            # Si es formato ISO datetime
            if 'T' in fecha_texto or '-' in fecha_texto:
                try:
                    return datetime.fromisoformat(fecha_texto.replace('Z', '+00:00'))
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")
        
        return None