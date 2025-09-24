from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SoyChileScraper(BaseScraper):
    def __init__(self):
        super().__init__('SoyChile')

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
            'base_url': 'https://www.soychile.cl',
            'search_url': 'https://www.soychile.cl/buscador?query=pymemad',
            'requires_selenium': True
        }

    def extract_news_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []

        try:
            if self.driver:
                wait = WebDriverWait(self.driver, 30)

                # Esperar que carguen los resultados
                print("Esperando que carguen los resultados...")
                time.sleep(5)

                # Esperar a que aparezca la lista de resultados
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "list-group")))
                print("Lista de resultados cargada")

                urls_procesadas = set()
                noticias_totales = 0

                # Obtener HTML actualizado
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

                # Buscar el contenedor de resultados (ul con class="list-group")
                lista_resultados = soup.find('ul', class_='list-group')

                if not lista_resultados:
                    self.logger.warning("No se encontró la lista de resultados")
                    return news_list

                # Buscar todos los artículos (li con class="list-group-item")
                articulos = lista_resultados.find_all('li', class_='list-group-item')
                print(f"Encontrados {len(articulos)} artículos")

                for articulo in articulos:
                    noticia = self.extraer_datos_articulo(articulo)
                    if noticia and noticia['url'] not in urls_procesadas:
                        urls_procesadas.add(noticia['url'])
                        news_list.append(noticia)
                        noticias_totales += 1
                        print(f"Noticia {noticias_totales}: {noticia['title'][:60]}...")

                # Intentar hacer scroll para cargar más resultados
                if self.driver:
                    print("Intentando cargar más resultados con scroll...")
                    for i in range(3):  # Hacer 3 scrolls
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)

                        # Actualizar soup
                        html_content = self.driver.page_source
                        soup = BeautifulSoup(html_content, 'html.parser')
                        lista_resultados = soup.find('ul', class_='list-group')

                        if lista_resultados:
                            nuevos_articulos = lista_resultados.find_all('li', class_='list-group-item')
                            for articulo in nuevos_articulos:
                                noticia = self.extraer_datos_articulo(articulo)
                                if noticia and noticia['url'] not in urls_procesadas:
                                    urls_procesadas.add(noticia['url'])
                                    news_list.append(noticia)
                                    noticias_totales += 1
                                    print(f"Noticia {noticias_totales}: {noticia['title'][:60]}...")

                print(f"Total artículos encontrados: {len(news_list)}")

        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extraer_datos_articulo(self, articulo):
        """Extraer datos de un artículo específico de SoyChile"""
        try:
            # Buscar el div con clase "info"
            info_div = articulo.find('div', class_='info')
            if not info_div:
                return None

            # Extraer título y URL del h2 > a
            h2 = info_div.find('h2')
            if not h2:
                return None

            titulo_link = h2.find('a')
            if not titulo_link:
                return None

            titulo = titulo_link.get_text().strip()
            url = titulo_link.get('href', '')

            # Construir URL completa si es necesario
            if url and not url.startswith('http'):
                url = 'https://www.soychile.cl' + url

            # Extraer fecha del span con clase "date"
            fecha_span = h2.find('span', class_='date')
            fecha_texto = fecha_span.get_text().strip() if fecha_span else None

            # Extraer imagen del div con clase "content-foto-buscador"
            img_div = articulo.find('div', class_='content-foto-buscador')
            img_url = ''
            if img_div:
                img = img_div.find('img')
                if img:
                    # Preferir data-src sobre src
                    img_url = img.get('data-src', img.get('src', ''))

            # Extraer excerpt del párrafo
            excerpt = ''
            p_excerpt = info_div.find('p', class_='truncate-overflow')
            if p_excerpt:
                # Remover los spans de fecha y media
                for span in p_excerpt.find_all('span'):
                    span.decompose()
                excerpt = p_excerpt.get_text().strip()

            # Solo devolver si tiene título y URL válidos
            if titulo and url:
                return {
                    'title': titulo,
                    'url': url,
                    'published_date_text': fecha_texto,  # Guardar para procesar después
                    'image_url': img_url,
                    'excerpt': excerpt
                }

        except Exception as e:
            self.logger.error(f"Error extrayendo artículo: {e}")

        return None

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

            # EXTRAER CONTENIDO - Basado en la estructura real de SoyChile
            contenido = ""

            # El contenido principal está en div con id="textoDetalle" y clase "note-inner-text"
            main_content = soup.find('div', {'id': 'textoDetalle', 'class': 'note-inner-text'})

            if not main_content:
                # Buscar alternativas
                main_content = soup.find('div', class_='note-inner-text')

            if not main_content:
                # Buscar dentro de note-inner-content
                main_content = soup.find('div', class_='note-inner-content')

            if main_content:
                # Limpiar scripts, estilos e iframes
                for script in main_content.find_all(['script', 'style', 'iframe']):
                    script.decompose()

                # Remover elementos no deseados
                for element in main_content.find_all(['a', 'button']):
                    if 'compartir' in element.get_text().lower():
                        element.decompose()

                # Obtener el texto directamente del contenedor
                # En SoyChile el texto está directamente en el div con <p></p> tags
                contenido_raw = str(main_content)

                # Reemplazar <p></p> con saltos de línea
                contenido_raw = contenido_raw.replace('<p></p>', '\n\n')

                # Crear un nuevo soup para procesar el contenido limpio
                content_soup = BeautifulSoup(contenido_raw, 'html.parser')

                # Obtener todo el texto
                contenido = content_soup.get_text().strip()

                # Limpiar espacios múltiples y saltos de línea excesivos
                contenido = re.sub(r'\n{3,}', '\n\n', contenido)
                contenido = re.sub(r' {2,}', ' ', contenido)

            if contenido:
                details['content'] = contenido.strip()
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido

            # EXTRAER FECHA - Buscar en div.media-content-autor
            fecha = None

            # Buscar el span con clase media-fecha-modificacion
            fecha_elem = soup.find('span', class_='media-fecha-modificacion')
            if fecha_elem:
                fecha_texto = fecha_elem.get_text().strip()
                # Formato: "13 de Septiembre de 2023 | 00:10"
                fecha = self.normalizar_fecha_soychile_detalle(fecha_texto)

            # Si no encontramos, buscar en meta tags
            if not fecha:
                meta_date = soup.find('meta', {'property': 'article:published_time'})
                if meta_date and meta_date.get('content'):
                    fecha = self.parse_iso_date(meta_date.get('content'))

            if fecha:
                details['published_date'] = fecha

            # EXTRAER IMAGEN - Del carrusel o imagen principal
            # Buscar en el carrusel de imágenes
            carousel = soup.find('div', class_='carousel')
            if carousel:
                img = carousel.find('img', class_='embed-responsive-item')
                if img and img.get('src'):
                    details['image_url'] = img.get('src')

            # Si no hay carousel, buscar en meta tags
            if not details['image_url']:
                meta_image = soup.find('meta', {'property': 'og:image'})
                if meta_image and meta_image.get('content'):
                    details['image_url'] = meta_image.get('content')

            # EXTRAER AUTOR - Generalmente no está visible en SoyChile
            # Podrías buscar en el texto del artículo patrones como "Por [nombre]"
            autor_match = re.search(r'Por\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)', contenido)
            if autor_match:
                details['author'] = autor_match.group(1).strip()

        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")

        return details

    def normalizar_fecha_soychile_detalle(self, fecha_texto):
        """Normalizar formato de fecha del detalle de SoyChile"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        try:
            # Formato: "13 de Septiembre de 2023 | 00:10"
            # Remover la hora
            fecha_limpia = fecha_texto.split('|')[0].strip()

            # Remover "de"
            fecha_limpia = fecha_limpia.replace(' de ', ' ')

            # Dividir en partes
            partes = fecha_limpia.split()

            if len(partes) >= 3:
                dia = int(partes[0])
                mes_nombre = partes[1].lower()
                año = int(partes[2])

                # Buscar el mes
                mes_num = meses.get(mes_nombre, None)

                if mes_num:
                    return datetime(año, mes_num, dia)

        except Exception as e:
            self.logger.error(f"Error normalizando fecha detalle '{fecha_texto}': {e}")

        return None

    def normalizar_fecha_soychile(self, fecha_texto):
        """Normalizar formato de fecha de SoyChile"""
        try:
            # Limpiar el texto
            fecha_limpia = fecha_texto.strip()

            # Formato común en SoyChile: "2022-7-18" o "18-07-2022"
            # También puede venir como "2022-07-18"

            # Intentar formato YYYY-M-D o YYYY-MM-DD
            match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', fecha_limpia)
            if match:
                año = int(match.group(1))
                mes = int(match.group(2))
                dia = int(match.group(3))
                return datetime(año, mes, dia)

            # Intentar formato D-M-YYYY o DD-MM-YYYY
            match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})', fecha_limpia)
            if match:
                dia = int(match.group(1))
                mes = int(match.group(2))
                año = int(match.group(3))
                return datetime(año, mes, dia)

            # Intentar formato con /
            fecha_limpia = fecha_limpia.replace('/', '-')
            match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})', fecha_limpia)
            if match:
                dia = int(match.group(1))
                mes = int(match.group(2))
                año = int(match.group(3))
                return datetime(año, mes, dia)

            print(f"No se pudo parsear la fecha: '{fecha_texto}'")

        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")

        return None

    def parse_iso_date(self, date_string):
        """Parsear fecha en formato ISO"""
        try:
            # Remover timezone si existe
            if 'T' in date_string:
                return datetime.fromisoformat(date_string.replace('Z', '+00:00').split('+')[0])
            else:
                return datetime.fromisoformat(date_string)
        except:
            return None
