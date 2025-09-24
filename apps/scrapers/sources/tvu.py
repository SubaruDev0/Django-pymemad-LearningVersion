from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TvuScraper(BaseScraper):
    def __init__(self):
        super().__init__('TVU')
        
    def get_source_config(self):
        return {
            'base_url': 'https://www.tvu.cl',
            'search_url': 'https://www.tvu.cl/search?s=pymemad',
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
                    
                    # Esperar que carguen los resultados
                    try:
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "main-search__list")))
                    except:
                        self.logger.warning("No se encontraron resultados en esta página")
                        break
                    
                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Buscar el contenedor de resultados
                    search_list = soup.find('div', class_='main-search__list')
                    
                    if not search_list:
                        self.logger.warning("No se encontró contenedor de resultados")
                        break
                    
                    # Buscar todos los items de búsqueda
                    items = search_list.find_all('div', class_='main-search__item')
                    self.logger.info(f"Encontrados {len(items)} items de búsqueda")
                    
                    for item in items:
                        noticia = self.extraer_datos_noticia(item)
                        if noticia:
                            news_list.append(noticia)
                            self.logger.info(f"Noticia encontrada: {noticia['title'][:60]}...")
                    
                    # Intentar ir a la siguiente página
                    if pagina_actual < max_paginas:
                        if not self.navegar_siguiente_pagina():
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
        """Extraer datos de una noticia específica de TVU"""
        try:
            # Buscar la tarjeta
            card = item.find('figure', class_='the-card')
            if not card:
                return None
            
            # Extraer URL y título
            titulo_elem = card.find('h1', class_='the-card__title')
            if not titulo_elem:
                return None
            
            link = titulo_elem.find('a')
            if not link:
                return None
            
            titulo = link.get_text().strip()
            url = link.get('href', '')
            
            # Asegurar URL completa
            if not url.startswith('http'):
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
    
    def navegar_siguiente_pagina(self):
        """Navegar a la siguiente página de resultados"""
        try:
            # Buscar paginación
            pagination = self.driver.find_elements(By.CSS_SELECTOR, ".pagination a, .pager a, .nav-links a")
            
            for link in pagination:
                texto = link.get_text().strip().lower()
                # Buscar enlaces de siguiente página
                if any(x in texto for x in ['siguiente', 'next', '»', '→']):
                    if link.is_displayed() and link.is_enabled():
                        self.logger.info("Navegando a siguiente página")
                        self.driver.execute_script("arguments[0].click();", link)
                        return True
            
            # Buscar por números de página
            current_url = self.driver.current_url
            if 'page=' in current_url or 'p=' in current_url:
                # Extraer número de página actual e incrementar
                match = re.search(r'(?:page|p)=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page = current_page + 1
                    next_url = re.sub(r'(?:page|p)=\d+', f'{match.group(0)[0]}={next_page}', current_url)
                    self.logger.info(f"Navegando a página {next_page}")
                    self.driver.get(next_url)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"No se encontró paginación: {e}")
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
            if self.driver:
                self.driver.get(news_url)
                time.sleep(3)
                html = self.driver.page_source
            else:
                import requests
                response = requests.get(news_url)
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar contenido principal
            contenido = ""
            
            # Buscar en diferentes selectores posibles para TVU
            contenido_selectores = [
                '.the-content',
                '.content-article',
                '.article-content',
                '.entry-content',
                '.post-content',
                'article .content',
                '.main-content',
                '[itemprop="articleBody"]'
            ]
            
            for selector in contenido_selectores:
                elemento = soup.select_one(selector)
                if elemento:
                    # Limpiar elementos no deseados
                    for unwanted in elemento.find_all(['script', 'style', '.sharedaddy', '.advertisement']):
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
            
            # Si no se encuentra contenido estructurado, buscar en el body
            if not contenido or len(contenido) < 100:
                # Buscar el artículo principal
                article = soup.find('article')
                if article:
                    paragrafos = article.find_all('p')
                    contenido = '\n\n'.join([p.get_text().strip() for p in paragrafos[:20] if p.get_text().strip()])
            
            if contenido:
                details['content'] = contenido[:5000]
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido
            
            # Buscar fecha
            # Buscar elemento de fecha del listado original
            fecha_selectores = [
                'date[datetime]',
                '.the-card__date',
                'time[datetime]',
                '.post-date',
                '.entry-date',
                '[class*="date"]'
            ]
            
            for selector in fecha_selectores:
                fecha_elem = soup.select_one(selector)
                if fecha_elem:
                    fecha_texto = ""
                    # Preferir el atributo datetime si existe
                    if fecha_elem.get('datetime'):
                        fecha_texto = fecha_elem.get('datetime')
                    else:
                        fecha_texto = fecha_elem.get_text().strip()
                    
                    if fecha_texto:
                        fecha_normalizada = self.normalizar_fecha_tvu(fecha_texto)
                        if fecha_normalizada:
                            details['published_date'] = fecha_normalizada
                            break
            
            # Buscar imagen
            img_selectores = [
                'img[src*="tvu"]',
                '.the-card__image',
                '.post-thumbnail img',
                '.featured-image img',
                'article img'
            ]
            
            for selector in img_selectores:
                img_elem = soup.select_one(selector)
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src', '')
                    if not src.startswith('http'):
                        src = urljoin(news_url, src)
                    details['image_url'] = src
                    break
            
            # Extraer categoría de la URL si es posible
            categoria = self.extraer_categoria_de_url(news_url)
            if categoria:
                details['author'] = categoria
                    
        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")
        
        return details
    
    def extraer_categoria_de_url(self, url):
        """Extraer categoría de la URL"""
        # TVU usa estructura: /prensa/[categoria]/fecha/titulo.html
        partes = url.split('/')
        
        if 'prensa' in partes:
            idx_prensa = partes.index('prensa')
            if idx_prensa + 1 < len(partes):
                categoria = partes[idx_prensa + 1]
                # Limpiar categoría
                if categoria and not categoria.isdigit():
                    return categoria.replace('-', ' ').title()
        
        return "Noticias"
    
    def normalizar_fecha_tvu(self, fecha_texto):
        """Normalizar formato de fecha de TVU"""
        # TVU usa formato: "15 de noviembre 2022"
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        try:
            # Si es formato ISO datetime
            if 'T' in fecha_texto or (fecha_texto.count('-') == 2 and len(fecha_texto) >= 10):
                try:
                    return datetime.fromisoformat(fecha_texto.replace('Z', '+00:00'))
                except:
                    pass
            
            # Quitar "de" y dividir
            fecha_limpia = fecha_texto.lower().replace(' de ', ' ')
            partes = fecha_limpia.split()
            
            if len(partes) >= 3:
                try:
                    dia = int(partes[0])
                    mes_nombre = partes[1]
                    año = int(partes[2])
                    
                    if mes_nombre in meses:
                        mes = meses[mes_nombre]
                        return datetime(año, mes, dia)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")
        
        return None