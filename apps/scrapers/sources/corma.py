from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.utils import timezone as django_timezone


class CormaScraper(BaseScraper):
    def __init__(self):
        super().__init__('CORMA')

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
                    print(f"Imagen actualizada: {news_data['image_url'][:80]}...")

                # Actualizar categoría/autor si no teníamos
                if news_data.get('author') and not news.author:
                    news.author = news_data['author']
                    updated = True
                    print(f"Categoría actualizada: {news_data['author']}")

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
            'base_url': 'https://www.corma.cl',
            'search_url': 'https://www.corma.cl/?s=PYMEMAD',
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

                # Esperar a que aparezca el contenedor de posts
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dslc-posts")))

                noticias_procesadas = set()
                scroll_count = 0
                max_scroll = 5
                altura_anterior = 0

                while scroll_count < max_scroll:
                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Buscar el contenedor de posts
                    posts_container = soup.find('div', class_='dslc-posts')

                    if not posts_container:
                        self.logger.warning("No se encontró contenedor de posts")
                        break

                    # Buscar todos los artículos
                    articulos = posts_container.find_all('div', class_='dslc-blog-post')
                    self.logger.info(f"Encontrados {len(articulos)} artículos en esta página")

                    # Procesar noticias nuevas
                    noticias_nuevas = 0
                    for articulo in articulos:
                        noticia = self.extraer_datos_articulo(articulo)
                        if noticia and noticia['url'] not in noticias_procesadas:
                            noticias_procesadas.add(noticia['url'])
                            news_list.append(noticia)
                            noticias_nuevas += 1
                            self.logger.info(f"Noticia encontrada: {noticia['title'][:60]}...")

                    self.logger.info(f"Scroll {scroll_count + 1}: {noticias_nuevas} noticias nuevas encontradas")

                    # Si no hay noticias nuevas, intentar scroll
                    if noticias_nuevas == 0:
                        # Hacer scroll hacia abajo
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)

                        # Verificar si la altura cambió
                        altura_actual = self.driver.execute_script("return document.body.scrollHeight")
                        if altura_actual == altura_anterior:
                            self.logger.info("No hay más contenido para cargar")
                            break
                        altura_anterior = altura_actual

                    scroll_count += 1

        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extraer_datos_articulo(self, articulo):
        """Extraer datos de un artículo específico de CORMA"""
        try:
            # Buscar el título
            titulo_elem = articulo.find('div', class_='dslc-blog-post-title')
            if not titulo_elem:
                return None

            h2 = titulo_elem.find('h2')
            if not h2:
                return None

            link = h2.find('a')
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
                time.sleep(4)
                html = self.driver.page_source
            else:
                import requests
                response = requests.get(news_url)
                html = response.text

            soup = BeautifulSoup(html, 'html.parser')

            # EXTRAER IMAGEN PRINCIPAL - Buscar en diferentes lugares
            # Primero buscar la imagen principal del post
            img_elem = soup.find('img', class_='wp-post-image')
            if img_elem:
                # Preferir srcset si existe para mejor calidad
                if img_elem.get('srcset'):
                    srcset = img_elem.get('srcset')
                    # Obtener la URL de mayor resolución
                    urls = re.findall(r'(https?://[^\s]+)', srcset)
                    if urls:
                        # La primera URL suele ser la de mayor calidad
                        details['image_url'] = urls[0]
                        print(f"Imagen encontrada en srcset: {details['image_url'][:80]}...")
                elif img_elem.get('src'):
                    details['image_url'] = img_elem.get('src')
                    print(f"Imagen encontrada: {details['image_url'][:80]}...")

            # Si no encontramos imagen principal, buscar en thumbnail
            if not details['image_url']:
                thumb_div = soup.find('div', class_='dslc-tp-thumbnail')
                if thumb_div:
                    img = thumb_div.find('img')
                    if img:
                        details['image_url'] = img.get('src', '')
                        print(f"Imagen encontrada en thumbnail: {details['image_url'][:80]}...")

            # EXTRAER FECHA - Estrategia alternativa: buscar el módulo específico con ID
            # Buscar el módulo que tiene la fecha (generalmente después del excerpt)
            fecha_encontrada = False

            # Estrategia 1: Buscar después del excerpt
            excerpt_module = soup.find('div', class_='dslc-tp-excerpt')
            if excerpt_module:
                # Buscar el siguiente módulo dslc-tp-meta después del excerpt
                siguiente = excerpt_module.find_next_sibling('div', class_='dslc-module-DSLC_TP_Meta')
                if siguiente:
                    meta_div = siguiente.find('div', class_='dslc-tp-meta')
                    if meta_div:
                        ul = meta_div.find('ul')
                        if ul:
                            # El primer li suele ser la fecha
                            primer_li = ul.find('li')
                            if primer_li and not primer_li.find('a'):
                                texto = primer_li.get_text().strip()
                                print(f"Fecha encontrada (método 1): {texto}")
                                fecha_normalizada = self.normalizar_fecha_corma(texto)
                                if fecha_normalizada:
                                    details['published_date'] = fecha_normalizada
                                    fecha_encontrada = True
                                    print(f"Fecha parseada: {fecha_normalizada}")

            # Estrategia 2: Buscar todos los li sin enlaces
            if not fecha_encontrada:
                print("Intentando método 2 para encontrar fecha...")
                todos_li = soup.find_all('li')
                for li in todos_li:
                    # Solo li que no tienen enlaces y están en un módulo dslc
                    if not li.find('a') and li.find_parent('div', class_='dslc-tp-meta'):
                        texto = li.get_text().strip()
                        # Verificar si parece una fecha
                        if re.search(r'\d{1,2}.*\d{4}', texto) and len(texto) < 50:
                            print(f"Fecha encontrada (método 2): {texto}")
                            fecha_normalizada = self.normalizar_fecha_corma(texto)
                            if fecha_normalizada:
                                details['published_date'] = fecha_normalizada
                                fecha_encontrada = True
                                print(f"Fecha parseada: {fecha_normalizada}")
                                break

            # EXTRAER CONTENIDO
            # Primero buscar el excerpt
            excerpt_div = soup.find('div', class_='dslc-tp-excerpt')
            if excerpt_div:
                details['excerpt'] = excerpt_div.get_text().strip()
                print(f"Excerpt encontrado: {len(details['excerpt'])} caracteres")

            # Buscar el contenido principal
            content_div = soup.find('div', class_='dslc-tp-content')
            if content_div:
                # Buscar dentro del theme-content-inner
                inner_content = content_div.find('div', id='dslc-theme-content-inner')
                if inner_content:
                    # Limpiar elementos no deseados
                    for unwanted in inner_content.find_all(['script', 'style', 'iframe', '.addtoany_shortcode']):
                        unwanted.decompose()

                    # Extraer párrafos
                    paragrafos = inner_content.find_all('p')
                    contenido_parrafos = []

                    for p in paragrafos:
                        texto = p.get_text().strip()
                        # Filtrar párrafos vacíos o muy cortos
                        if texto and len(texto) > 20 and not texto.startswith('&nbsp;'):
                            contenido_parrafos.append(texto)

                    if contenido_parrafos:
                        details['content'] = '\n\n'.join(contenido_parrafos)
                        print(f"Contenido extraído: {len(details['content'])} caracteres")

            # Si no tenemos excerpt, crear uno del contenido
            if not details['excerpt'] and details['content']:
                details['excerpt'] = details['content'][:200] + '...' if len(details['content']) > 200 else details[
                    'content']

            # EXTRAER CATEGORÍAS - Buscar en el primer módulo de meta
            cat_module = soup.find('div', class_='dslc-module-DSLC_TP_Meta')
            if cat_module:
                ul = cat_module.find('ul')
                if ul:
                    # Buscar enlaces de categorías
                    cat_links = ul.find_all('a')
                    categorias = []
                    for link in cat_links:
                        cat_text = link.get_text().strip()
                        if cat_text and cat_text not in categorias:
                            categorias.append(cat_text)

                    if categorias:
                        details['author'] = ', '.join(categorias)
                        print(f"Categorías encontradas: {details['author']}")

        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")
            import traceback
            print(traceback.format_exc())

        return details

    def normalizar_fecha_corma(self, fecha_texto):
        """Normalizar formato de fecha de CORMA"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }

        try:
            # Si es formato ISO datetime
            if 'T' in fecha_texto or (fecha_texto.count('-') == 2 and len(fecha_texto) >= 10):
                try:
                    fecha_dt = datetime.fromisoformat(fecha_texto.replace('Z', '+00:00'))
                    return django_timezone.make_aware(fecha_dt)
                except:
                    pass

            # Limpiar el texto
            fecha_limpia = fecha_texto.strip().lower()
            # Remover comas
            fecha_limpia = fecha_limpia.replace(',', '')

            # Buscar patrón día mes año (ej: "2 junio 2025")
            for mes_esp, mes_num in meses.items():
                if mes_esp in fecha_limpia:
                    # Buscar el patrón con el mes
                    pattern = r'(\d{1,2})\s+' + mes_esp + r'\s+(\d{4})'
                    match = re.search(pattern, fecha_limpia)
                    if match:
                        dia = int(match.group(1))
                        año = int(match.group(2))
                        fecha_dt = datetime(año, mes_num, dia)
                        # Hacer timezone-aware
                        fecha_dt = django_timezone.make_aware(fecha_dt)
                        print(f"Fecha parseada correctamente: {fecha_texto} -> {fecha_dt}")
                        return fecha_dt

            # Intentar otro formato: mes día, año
            match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', fecha_limpia)
            if match:
                mes_nombre = match.group(1)
                dia = int(match.group(2))
                año = int(match.group(3))

                for mes_key, mes_num in meses.items():
                    if mes_key == mes_nombre or mes_nombre.startswith(mes_key):
                        fecha_dt = datetime(año, mes_num, dia)
                        fecha_dt = django_timezone.make_aware(fecha_dt)
                        print(f"Fecha parseada (formato 2): {fecha_texto} -> {fecha_dt}")
                        return fecha_dt

        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")
            print(f"Error parseando fecha: {e}")

        return None
