from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class GoreScraper(BaseScraper):
    def __init__(self):
        super().__init__('GORE Biobío')

    def save_news(self, news_data):
        """Override para actualizar noticias existentes"""
        try:
            from apps.news.models import News

            # Verificar qué datos estamos intentando guardar
            print(f"Procesando: {news_data.get('title', 'Sin título')[:50]}...")

            # Buscar si ya existe
            try:
                news = News.objects.get(url=news_data['url'])
                # Ya existe - actualizar
                updated = False

                # Actualizar fecha si tenemos una nueva y es diferente
                if news_data.get('published_date') and news.published_date != news_data['published_date']:
                    news.published_date = news_data['published_date']
                    updated = True
                    print(f"Fecha actualizada: {news_data['published_date']}")

                # Actualizar contenido si es más largo o si no teníamos
                if news_data.get('content'):
                    if not news.content or len(news_data['content']) > len(news.content):
                        news.content = news_data['content']
                        news.excerpt = news_data.get('excerpt', '')
                        updated = True
                        print(f"Contenido actualizado: {len(news_data['content'])} caracteres")

                # Actualizar imagen si es diferente o no teníamos
                if news_data.get('image_url') and news.image_url != news_data['image_url']:
                    news.image_url = news_data['image_url']
                    updated = True
                    print(f"Imagen actualizada: {news_data['image_url']}")

                # Actualizar autor si no teníamos
                if news_data.get('author') and not news.author:
                    news.author = news_data['author']
                    updated = True
                    print(f"Autor actualizado: {news_data['author']}")

                if updated:
                    news.save()
                    print(f"✅ Actualizada: {news_data['title'][:50]}...")
                    return True
                else:
                    print(f"Sin cambios: {news_data['title'][:50]}...")
                    return False

            except News.DoesNotExist:
                # No existe - crear nueva
                news = News.objects.create(
                    source=self.source,
                    title=news_data.get('title', ''),
                    url=news_data['url'],
                    content=news_data.get('content', ''),
                    excerpt=news_data.get('excerpt', ''),
                    published_date=news_data.get('published_date'),
                    image_url=news_data.get('image_url', ''),
                    author=news_data.get('author', ''),
                )
                print(f"✅ Nueva noticia guardada: {news_data['title'][:50]}...")
                return True

        except Exception as e:
            print(f"Error guardando/actualizando noticia: {e}")
            print(f"Datos problemáticos: {news_data}")
            import traceback
            print(traceback.format_exc())
            return False

    def get_source_config(self):
        return {
            'base_url': 'https://gorebiobio.cl',
            'search_url': 'https://gorebiobio.cl/?s=pymemad',
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

                    # Esperar que cargue el grid de noticias
                    try:
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "w-grid-list")))
                    except:
                        self.logger.warning("No se encontró el grid de noticias")
                        # Intentar con selector alternativo
                        try:
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "w-grid-item")))
                        except:
                            self.logger.warning("No se encontraron resultados")
                            break

                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Buscar el contenedor principal del grid
                    grid_list = soup.find('div', class_='w-grid-list')

                    if grid_list:
                        # Buscar todos los artículos dentro del grid
                        articulos = grid_list.find_all('article', class_='w-grid-item')
                    else:
                        # Buscar artículos directamente
                        articulos = soup.find_all('article', class_='w-grid-item')

                    self.logger.info(f"Encontrados {len(articulos)} artículos")

                    for articulo in articulos:
                        noticia = self.extraer_datos_articulo(articulo)
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
            print(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extraer_datos_articulo(self, articulo):
        """Extraer datos de un artículo específico de GORE"""
        try:
            # Buscar el título
            titulo_elem = articulo.find(class_=re.compile(r'post_title'))
            if not titulo_elem:
                # Buscar alternativa
                titulo_elem = articulo.find('h2', class_=re.compile(r'entry-title'))

            if not titulo_elem:
                return None

            # Buscar el enlace dentro del título
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
            print(f"Error extrayendo artículo: {e}")

        return None

    def navegar_siguiente_pagina(self):
        """Navegar a la siguiente página de resultados"""
        try:
            # Buscar paginación - GORE puede usar diferentes sistemas

            # Opción 1: Botón "Siguiente" o "Next"
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                     "a.next, a[rel='next'], .pagination .next, .nav-next a, .page-numbers.next")

            for button in next_buttons:
                if button.is_displayed() and button.is_enabled():
                    self.logger.info("Navegando a siguiente página")
                    self.driver.execute_script("arguments[0].click();", button)
                    return True

            # Opción 2: Números de página
            pagination = self.driver.find_elements(By.CSS_SELECTOR,
                                                   ".pagination a, .page-numbers")

            current_page = None
            for elem in pagination:
                if 'current' in elem.get_attribute('class'):
                    try:
                        current_page = int(elem.get_text().strip())
                        break
                    except:
                        pass

            if current_page:
                # Buscar siguiente número
                for elem in pagination:
                    try:
                        page_num = int(elem.get_text().strip())
                        if page_num == current_page + 1:
                            self.logger.info(f"Navegando a página {page_num}")
                            self.driver.execute_script("arguments[0].click();", elem)
                            return True
                    except:
                        pass

            # Opción 3: Scroll infinito
            # GORE podría usar carga dinámica
            old_height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height > old_height:
                self.logger.info("Cargadas más noticias mediante scroll")
                return True

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
            if self.driver:
                self.driver.get(news_url)
                time.sleep(3)
                html = self.driver.page_source
            else:
                import requests
                response = requests.get(news_url)
                html = response.text

            soup = BeautifulSoup(html, 'html.parser')

            # EXTRAER CONTENIDO - Basado en la estructura real de GORE
            contenido = ""

            # El contenido principal está en div con clase "post_content textojustificado"
            contenido_elem = soup.find('div', class_=re.compile(r'post_content.*textojustificado'))

            if not contenido_elem:
                # Buscar alternativas
                contenido_elem = soup.find('div', class_='w-post-elm post_content')

            if not contenido_elem:
                contenido_elem = soup.find('div', class_='post_content')

            if contenido_elem:
                # Limpiar elementos no deseados
                for unwanted in contenido_elem.find_all(['script', 'style', 'figure']):
                    unwanted.decompose()

                # Buscar listas y párrafos
                elementos_contenido = []

                # Procesar listas ul/ol
                for lista in contenido_elem.find_all(['ul', 'ol']):
                    for item in lista.find_all('li'):
                        texto = item.get_text().strip()
                        if texto:
                            elementos_contenido.append(f"• {texto}")

                # Procesar párrafos
                for p in contenido_elem.find_all('p'):
                    texto = p.get_text().strip()
                    if texto and len(texto) > 10:
                        elementos_contenido.append(texto)

                contenido = '\n\n'.join(elementos_contenido)

            if contenido:
                details['content'] = contenido.strip()
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido

            # EXTRAER FECHA - Buscar el elemento time con datetime
            fecha_elem = soup.find('time', {'datetime': True})
            if fecha_elem:
                # Obtener del atributo datetime
                fecha_iso = fecha_elem.get('datetime')
                if fecha_iso:
                    fecha = self.parse_datetime_iso(fecha_iso)
                    if fecha:
                        details['published_date'] = fecha
                        print(f"Fecha extraída: {fecha_iso} -> {fecha}")
                else:
                    # Intentar del texto (formato: 12/09/2022)
                    fecha_texto = fecha_elem.get_text().strip()
                    fecha = self.normalizar_fecha_gore(fecha_texto)
                    if fecha:
                        details['published_date'] = fecha

            # EXTRAER IMAGEN - Buscar en el div con clase post_image
            img_div = soup.find('div', class_='w-post-elm post_image')
            if img_div:
                img_elem = img_div.find('img')
                if img_elem and img_elem.get('src'):
                    img_url = img_elem.get('src')
                    # Asegurar URL completa
                    if not img_url.startswith('http'):
                        img_url = urljoin(news_url, img_url)
                    details['image_url'] = img_url
                    print(f"Imagen extraída: {img_url}")

            # Si no se encuentra, buscar cualquier imagen grande en el artículo
            if not details['image_url']:
                article = soup.find('article')
                if article:
                    for img in article.find_all('img'):
                        src = img.get('src', '')
                        # Filtrar imágenes pequeñas o iconos
                        if src and 'uploads' in src and not any(x in src for x in ['thumb', 'icon', '-150x', '-300x']):
                            if not src.startswith('http'):
                                src = urljoin(news_url, src)
                            details['image_url'] = src
                            break

            # EXTRAER CATEGORÍA/AUTOR - En GORE aparece como categoría
            categoria_elem = soup.find('div', class_='w-post-elm post_taxonomy')
            if categoria_elem:
                cat_link = categoria_elem.find('a')
                if cat_link:
                    # Buscar el span con la etiqueta
                    label = cat_link.find('span', class_='w-btn-label')
                    if label:
                        details['author'] = label.get_text().strip()
                    else:
                        details['author'] = cat_link.get_text().strip()

        except Exception as e:
            print(f"Error extrayendo detalles de {news_url}: {e}")

        return details

    def parse_datetime_iso(self, datetime_str):
        """Parsear fecha en formato ISO con timezone"""
        try:
            # Formato ejemplo: "2022-09-12T17:55:46-03:00"
            # Remover timezone para simplificar
            if 'T' in datetime_str:
                fecha_parte = datetime_str.split('T')[0]
                año, mes, dia = fecha_parte.split('-')
                return datetime(int(año), int(mes), int(dia))
        except Exception as e:
            print(f"Error parseando datetime ISO '{datetime_str}': {e}")
        return None

    def normalizar_fecha_gore(self, fecha_texto):
        """Normalizar formato de fecha de GORE"""
        try:
            # Formato: DD/MM/YYYY (12/09/2022)
            if '/' in fecha_texto:
                partes = fecha_texto.split('/')
                if len(partes) == 3:
                    dia = int(partes[0])
                    mes = int(partes[1])
                    año = int(partes[2])
                    return datetime(año, mes, dia)

        except Exception as e:
            print(f"Error normalizando fecha '{fecha_texto}': {e}")

        return None
