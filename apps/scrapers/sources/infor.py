from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class InforScraper(BaseScraper):
    def __init__(self):
        super().__init__('INFOR')
        
    def get_source_config(self):
        return {
            'base_url': 'https://lme.infor.cl',
            'search_url': 'https://lme.infor.cl/index.php/component/search/?searchword=pymemad&ordering=newest&searchphrase=all&limit=20',
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
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pagelistcont")))
                    except:
                        self.logger.warning("No se encontraron resultados en esta página")
                        break
                    
                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Buscar todos los contenedores de noticias
                    contenedores = soup.find_all('div', class_='pagelistcont')
                    self.logger.info(f"Encontrados {len(contenedores)} contenedores de noticias")
                    
                    for contenedor in contenedores:
                        noticia = self.extraer_datos_noticia(contenedor)
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
    
    def extraer_datos_noticia(self, contenedor):
        """Extraer datos de una noticia específica de INFOR"""
        try:
            # Buscar el box de noticia
            box = contenedor.find('div', class_='box-not')
            if not box:
                return None
            
            # Extraer título y URL
            titulo_elem = box.find('h3')
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
            # Buscar enlaces de paginación
            pagination = self.driver.find_element(By.CLASS_NAME, "pagination")
            
            # Buscar el enlace "Siguiente" o números de página
            next_links = pagination.find_elements(By.TAG_NAME, "a")
            
            for link in next_links:
                texto = link.get_text().strip()
                # Buscar enlaces con "Siguiente", "Next", "»" o números
                if any(x in texto.lower() for x in ['siguiente', 'next', '»']) or texto.isdigit():
                    # Verificar si no está deshabilitado
                    if 'disabled' not in link.get_attribute('class'):
                        self.logger.info(f"Navegando a: {texto}")
                        self.driver.execute_script("arguments[0].click();", link)
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
            
            # Buscar en diferentes selectores posibles para INFOR
            contenido_selectores = [
                '.item-page',
                '.article-content',
                '.content',
                'article',
                '.container3 .row'
            ]
            
            for selector in contenido_selectores:
                elemento = soup.select_one(selector)
                if elemento:
                    # Limpiar elementos no deseados
                    for unwanted in elemento.find_all(['script', 'style', '.breadcrumb', '.pagination']):
                        unwanted.decompose()
                    
                    # Buscar párrafos dentro del elemento
                    paragrafos = elemento.find_all('p')
                    if paragrafos:
                        contenido_parrafos = []
                        for p in paragrafos:
                            texto = p.get_text().strip()
                            if texto and len(texto) > 20:  # Filtrar párrafos muy cortos
                                contenido_parrafos.append(texto)
                        
                        if contenido_parrafos:
                            contenido = '\n\n'.join(contenido_parrafos)
                            break
            
            # Si no se encuentra contenido estructurado, buscar en el body
            if not contenido or len(contenido) < 100:
                body = soup.find('body')
                if body:
                    # Buscar el contenedor principal
                    main_content = body.find('div', class_='container3')
                    if main_content:
                        paragrafos = main_content.find_all('p')
                        contenido = '\n\n'.join([p.get_text().strip() for p in paragrafos[:20] if p.get_text().strip()])
            
            if contenido:
                details['content'] = contenido[:5000]
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido
            
            # Buscar fecha en la lista de resultados original
            # Ya que INFOR muestra la fecha "Creado el DD Mes YYYY" en los resultados
            # Intentaremos extraerla del contenido de la página
            fecha_patrones = [
                r'Creado el (\d{1,2} \w+ \d{4})',
                r'(\d{1,2} \w+ \d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ]
            
            for patron in fecha_patrones:
                match = re.search(patron, html)
                if match:
                    fecha_texto = match.group(1)
                    fecha_normalizada = self.normalizar_fecha_infor(fecha_texto)
                    if fecha_normalizada:
                        details['published_date'] = fecha_normalizada
                        break
            
            # Buscar imagen
            img_selectores = [
                'img[src*="infor"]',
                '.item-page img',
                'article img',
                'img[class*="article"]'
            ]
            
            for selector in img_selectores:
                img_elem = soup.select_one(selector)
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src', '')
                    if not src.startswith('http'):
                        src = urljoin(news_url, src)
                    details['image_url'] = src
                    break
            
            # Buscar categoría
            cat_elem = soup.find('p', class_='doc-det')
            if cat_elem:
                cat_text = cat_elem.get_text()
                if 'Categoría:' in cat_text:
                    details['author'] = cat_text.replace('Categoría:', '').strip()
                    
        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")
        
        return details
    
    def normalizar_fecha_infor(self, fecha_texto):
        """Normalizar formato de fecha de INFOR"""
        # INFOR usa formato: "19 Diciembre 2022"
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        try:
            # Dividir la fecha
            partes = fecha_texto.strip().split()
            if len(partes) >= 3:
                dia = int(partes[0])
                mes_nombre = partes[1].lower()
                año = int(partes[2])
                
                if mes_nombre in meses:
                    mes = meses[mes_nombre]
                    return datetime(año, mes, dia)
                    
        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")
        
        return None