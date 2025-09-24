from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SenadoScraper(BaseScraper):
    def __init__(self):
        super().__init__('Senado Chile')

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
            'base_url': 'https://www.senado.cl',
            'search_url': 'https://www.senado.cl/search?search=pymemad',
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

                # Esperar que aparezcan las tarjetas de noticias
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.card")))
                    print("Resultados de búsqueda cargados")
                except:
                    self.logger.warning("No se encontraron resultados")
                    return news_list

                # Procesar resultados con scroll para cargar más
                max_scrolls = 5
                scroll_actual = 0
                urls_procesadas = set()

                while scroll_actual < max_scrolls:
                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Buscar todas las tarjetas de noticias
                    # Estructura: <a class="card color-blue-100 link-reset d-block mb-4" href="...">
                    tarjetas = soup.find_all('a', class_=re.compile(r'card.*link-reset'))

                    print(f"Encontradas {len(tarjetas)} tarjetas en scroll {scroll_actual + 1}")

                    nuevas_noticias = 0
                    for tarjeta in tarjetas:
                        noticia = self.extraer_datos_tarjeta(tarjeta)
                        if noticia and noticia['url'] not in urls_procesadas:
                            urls_procesadas.add(noticia['url'])
                            news_list.append(noticia)
                            nuevas_noticias += 1
                            print(f"Noticia encontrada: {noticia['title'][:60]}...")

                    # Si no hay nuevas noticias, terminar
                    if nuevas_noticias == 0:
                        print("No se encontraron nuevas noticias en este scroll")
                        break

                    # Hacer scroll para cargar más
                    if scroll_actual < max_scrolls - 1:
                        old_height = self.driver.execute_script("return document.body.scrollHeight")
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        new_height = self.driver.execute_script("return document.body.scrollHeight")

                        if new_height == old_height:
                            print("No hay más contenido para cargar")
                            break

                    scroll_actual += 1

                print(f"Total noticias encontradas: {len(news_list)}")

        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extraer_datos_tarjeta(self, tarjeta):
        """Extraer datos de una tarjeta de noticia del Senado"""
        try:
            # La tarjeta misma es un enlace
            url = tarjeta.get('href', '')
            if not url:
                return None

            # Asegurar URL completa
            if not url.startswith('http'):
                url = urljoin(self.get_source_config()['base_url'], url)

            # Buscar el contenedor interno
            contenedor = tarjeta.find('div', class_='p-2')
            if not contenedor:
                return None

            # Extraer título (está en un h3)
            titulo_elem = contenedor.find('h3', class_='text--md')
            if not titulo_elem:
                return None

            titulo = titulo_elem.get_text().strip()

            # Extraer fecha (está en un p con la fecha)
            fecha_texto = None
            parrafos = contenedor.find_all('p', class_='text--md')
            for p in parrafos:
                texto = p.get_text().strip()
                # Buscar patrón de fecha
                if re.search(r'\d+\s+de\s+\w+\s+de\s+\d{4}', texto):
                    fecha_texto = texto
                    break

            # Extraer descripción/excerpt
            desc_id = tarjeta.get('id', '')
            if desc_id:
                desc_elem = contenedor.find('div', id=f'desc{desc_id}')
                if desc_elem:
                    excerpt = desc_elem.get_text().strip()
                else:
                    excerpt = ''
            else:
                # Buscar cualquier div con descripción
                desc_elem = contenedor.find('p', class_=lambda x: x != 'text--md')
                excerpt = desc_elem.get_text().strip() if desc_elem else ''

            # Solo devolver si tiene título y URL válidos
            if titulo and url:
                return {
                    'title': titulo,
                    'url': url,
                    'published_date_text': fecha_texto,
                    'excerpt': excerpt
                }

        except Exception as e:
            self.logger.error(f"Error extrayendo tarjeta: {e}")

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

            # EXTRAER CONTENIDO - Buscar en el main o article
            contenido = ""

            # El contenido principal está en el main
            main_elem = soup.find('main')
            if not main_elem:
                # Buscar en article
                main_elem = soup.find('article')

            if main_elem:
                # Buscar el div con clase dynamic-content primero
                content_div = main_elem.find('div', class_='dynamic-content')

                if content_div:
                    # Limpiar elementos no deseados
                    for unwanted in content_div.find_all(['script', 'style', 'img']):
                        unwanted.decompose()

                    # Extraer párrafos
                    paragrafos = content_div.find_all('p')
                    contenido_parrafos = []

                    for p in paragrafos:
                        texto = p.get_text().strip()
                        # Filtrar párrafos vacíos o con solo &nbsp;
                        if texto and texto != '\xa0' and len(texto) > 10:
                            contenido_parrafos.append(texto)

                    contenido = '\n\n'.join(contenido_parrafos)

                # Si no hay dynamic-content, buscar párrafos directamente
                if not contenido:
                    paragrafos = main_elem.find_all('p')
                    contenido_parrafos = []

                    for p in paragrafos:
                        texto = p.get_text().strip()
                        if texto and len(texto) > 20:
                            # Evitar metadata
                            if not any(x in texto.lower() for x in ['compartir', 'martes', 'lunes', 'miércoles']):
                                contenido_parrafos.append(texto)

                    contenido = '\n\n'.join(contenido_parrafos[:20])  # Limitar a 20 párrafos

            if contenido:
                details['content'] = contenido.strip()
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido

            # EXTRAER FECHA - Buscar en los párrafos con formato de fecha
            fecha_elem = soup.find('p', class_='text--md', string=re.compile(r'\w+\s+\d+\s+de\s+\w+\s+de\s+\d{4}'))
            if fecha_elem:
                fecha_texto = fecha_elem.get_text().strip()
                fecha = self.normalizar_fecha_senado(fecha_texto)
                if fecha:
                    details['published_date'] = fecha
                    print(f"Fecha extraída: {fecha_texto} -> {fecha}")

            # EXTRAER IMAGEN - Buscar en figure o img
            figure = soup.find('figure', class_='figure')
            if figure:
                img = figure.find('img')
                if img:
                    # Preferir src sobre srcset
                    img_url = img.get('src', '')
                    if not img_url and img.get('srcset'):
                        # Extraer primera URL del srcset
                        srcset = img.get('srcset', '')
                        if srcset:
                            primera_url = srcset.split(',')[0].split(' ')[0]
                            img_url = primera_url

                    if img_url:
                        # Limpiar y completar URL
                        if img_url.startswith('/_next/image?url='):
                            # Extraer URL real del parámetro
                            import urllib.parse
                            parsed = urllib.parse.urlparse(img_url)
                            params = urllib.parse.parse_qs(parsed.query)
                            if 'url' in params:
                                img_url = params['url'][0]

                        if not img_url.startswith('http'):
                            img_url = urljoin(news_url, img_url)

                        details['image_url'] = img_url
                        print(f"Imagen extraída: {img_url}")

            # EXTRAER CATEGORÍA como autor
            categoria_elem = soup.find('p', class_='text--md bold uppercase title--line')
            if not categoria_elem:
                # Buscar en los primeros párrafos
                for p in soup.find_all('p', class_='text--md'):
                    texto = p.get_text().strip()
                    if texto and texto.isupper() and len(texto) < 50:
                        details['author'] = texto
                        break

        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")

        return details

    def normalizar_fecha_senado(self, fecha_texto):
        """Normalizar formato de fecha del Senado"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        try:
            # Formato: "Martes 4 de Agosto de 2015" o "7 de junio de 2024"
            # Limpiar el texto
            fecha_limpia = fecha_texto.strip()

            # Remover el día de la semana si existe
            dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
            for dia in dias_semana:
                fecha_limpia = re.sub(f'^{dia}\\s+', '', fecha_limpia, flags=re.IGNORECASE)

            # Buscar patrón: "DD de MES de YYYY"
            match = re.search(r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_limpia, re.IGNORECASE)

            if match:
                dia = int(match.group(1))
                mes_nombre = match.group(2).lower()
                año = int(match.group(3))

                # Buscar el mes
                mes_num = meses.get(mes_nombre, None)

                if mes_num:
                    return datetime(año, mes_num, dia)
                else:
                    print(f"Mes no reconocido: '{mes_nombre}'")

        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")

        return None
