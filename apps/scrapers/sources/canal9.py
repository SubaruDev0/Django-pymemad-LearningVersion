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


class Canal9Scraper(BaseScraper):
    def __init__(self):
        super().__init__('Canal 9')

    def save_news(self, news_data):
        """Override para actualizar noticias existentes"""
        try:
            from apps.news.models import News

            # Verificar qué datos estamos intentando guardar
            print(f"Procesando: {news_data.get('title', 'Sin título')[:50]}...")

            # Si hay video_url, guardarlo como imagen o crear una URL corta
            if news_data.get('video_url'):
                # Opción 1: Guardar solo una referencia corta
                news_data['image_url'] = 'VIDEO_CANAL9'
                # O puedes extraer el ID del video si es posible
                video_match = re.search(r'/vod/([^?]+)', news_data['video_url'])
                if video_match:
                    video_id = video_match.group(1)
                    news_data['image_url'] = f'https://rudo.video/vod/{video_id}'

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

                # Actualizar imagen si es diferente
                if news_data.get('image_url') and news.image_url != news_data['image_url']:
                    # Truncar si es muy larga
                    if len(news_data['image_url']) > 200:
                        news_data['image_url'] = news_data['image_url'][:200]
                    news.image_url = news_data['image_url']
                    updated = True
                    print(f"Media actualizado: {news_data['image_url'][:50]}...")

                if updated:
                    news.save()
                    print(f"✅ Actualizada: {news_data['title'][:50]}...")
                    return True
                else:
                    print(f"Sin cambios: {news_data['title'][:50]}...")
                    return False

            except News.DoesNotExist:
                # No existe - crear nueva
                # Truncar campos si son muy largos
                if news_data.get('image_url') and len(news_data['image_url']) > 200:
                    news_data['image_url'] = news_data['image_url'][:200]

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
            'base_url': 'https://www.canal9.cl',
            'search_url': 'https://www.canal9.cl/buscador/Pymemad',
            'requires_selenium': True
        }

    def extract_news_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []

        try:
            # Dar tiempo para que cargue el contenido dinámico
            if self.driver:
                time.sleep(8)

                # Hacer scroll para cargar más contenido
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(4)

                # Obtener el HTML actualizado después del scroll
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

            # Buscar artículos (estructura moderna de Canal 9)
            articulos = soup.find_all('article')

            if not articulos:
                # Buscar por estructura alternativa
                contenedor = soup.find('div', class_=re.compile(r'md:w-full.*md:flex.*'))
                if contenedor:
                    articulos = contenedor.find_all('article')

            print(f"Encontrados {len(articulos)} artículos")

            for articulo in articulos:
                try:
                    # Buscar enlaces con /episodios/
                    enlaces = articulo.find_all('a', href=True)
                    url = None

                    for enlace in enlaces:
                        href = enlace.get('href', '')
                        if '/episodios/' in href:
                            url = href
                            break

                    if not url:
                        continue

                    # Asegurar URL completa
                    if not url.startswith('http'):
                        url = urljoin(self.get_source_config()['base_url'], url)

                    # Extraer título
                    titulo = ""
                    h3 = articulo.find('h3')
                    if h3:
                        titulo = h3.get_text().strip()

                    if not titulo:
                        continue

                    news_list.append({
                        'title': titulo,
                        'url': url
                    })
                    print(f"Noticia encontrada: {titulo[:60]}...")

                except Exception as e:
                    self.logger.error(f"Error procesando artículo: {e}")

        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extract_news_details(self, news_url):
        details = {
            'content': '',
            'excerpt': '',
            'published_date': None,
            'image_url': '',
            'video_url': '',
            'author': ''
        }

        try:
            if self.driver:
                self.driver.get(news_url)
                time.sleep(5)  # Más tiempo para cargar el contenido
                html = self.driver.page_source
            else:
                import requests
                response = requests.get(news_url)
                html = response.text

            soup = BeautifulSoup(html, 'html.parser')

            # EXTRAER FECHA - Buscar el formato específico de Canal 9
            # Formato: "30 September 2024 | 14:00 hrs"
            fecha_elem = soup.find('p', class_=re.compile(r'heading-14px.*text-\[#94A3B8\]'))
            if fecha_elem:
                fecha_texto = fecha_elem.get_text().strip()
                print(f"Fecha encontrada: {fecha_texto}")

                # Separar fecha y hora
                if '|' in fecha_texto:
                    fecha_parte = fecha_texto.split('|')[0].strip()
                else:
                    fecha_parte = fecha_texto.strip()

                fecha_normalizada = self.normalizar_fecha_canal9(fecha_parte)
                if fecha_normalizada:
                    details['published_date'] = fecha_normalizada
                    print(f"Fecha parseada: {fecha_normalizada}")

            # EXTRAER VIDEO - Buscar iframe de video
            video_iframe = soup.find('iframe', src=re.compile(r'rudo\.video|youtube|vimeo'))
            if video_iframe:
                video_url = video_iframe.get('src', '')
                if video_url:
                    details['video_url'] = video_url

                    # Extraer una versión corta para image_url
                    # Opción 1: Extraer solo el ID del video
                    video_match = re.search(r'/vod/([^?]+)', video_url)
                    if video_match:
                        video_id = video_match.group(1)
                        details['image_url'] = f'https://rudo.video/vod/{video_id}'
                    else:
                        # Opción 2: Guardar indicador de que hay video
                        details['image_url'] = 'VIDEO_DISPONIBLE'

                    print(f"Video encontrado: {video_url[:80]}...")

            # Si no hay video, buscar imagen
            if not details['image_url']:
                # Buscar en diferentes lugares
                img_selectors = [
                    'img[src*="media.canal9.cl"]',
                    'img[srcset*="media.canal9.cl"]',
                    '.post-image img',
                    'article img'
                ]

                for selector in img_selectors:
                    img_elem = soup.select_one(selector)
                    if img_elem:
                        # Preferir srcset si existe
                        if img_elem.get('srcset'):
                            # Obtener la imagen más grande del srcset
                            srcset = img_elem.get('srcset')
                            urls = re.findall(r'(https?://[^\s]+)', srcset)
                            if urls:
                                details['image_url'] = urls[-1]  # Última URL suele ser la más grande
                                print(f"Imagen encontrada en srcset: {details['image_url']}")
                                break
                        elif img_elem.get('src'):
                            details['image_url'] = img_elem.get('src')
                            print(f"Imagen encontrada: {details['image_url']}")
                            break

            # EXTRAER CONTENIDO - Buscar en la estructura específica
            contenido_completo = []

            # Primero buscar el párrafo principal con borde azul
            parrafo_destacado = soup.find('p', class_=re.compile(r'border-l-3px.*border-l-#3573F2'))
            if parrafo_destacado:
                texto_destacado = parrafo_destacado.get_text().strip()
                if texto_destacado:
                    contenido_completo.append(texto_destacado)
                    print("Párrafo destacado encontrado")

            # Luego buscar contenido en divs con md:px-45px
            contenido_divs = soup.find_all('div', class_=re.compile(r'md:px-45px'))

            for div in contenido_divs:
                # Buscar párrafos dentro de cada div
                parrafos = div.find_all('p', class_=re.compile(r'font-medium.*leading-26px'))

                for p in parrafos:
                    texto = p.get_text().strip()
                    # Filtrar contenido repetido y muy corto
                    if texto and len(texto) > 30 and texto not in contenido_completo:
                        contenido_completo.append(texto)

            # Si no encontramos con esos selectores, buscar alternativa
            if len(contenido_completo) < 2:
                # Buscar en el contenedor principal
                content_div = soup.find('div', class_='content')
                if content_div:
                    parrafos = content_div.find_all('p')
                    for p in parrafos:
                        texto = p.get_text().strip()
                        if texto and len(texto) > 30 and texto not in contenido_completo:
                            contenido_completo.append(texto)

            # Unir todo el contenido
            if contenido_completo:
                contenido = '\n\n'.join(contenido_completo)
                details['content'] = contenido[:5000]  # Limitar a 5000 caracteres
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido
                print(f"Contenido extraído: {len(contenido)} caracteres")

            # BUSCAR AUTOR (generalmente no está presente en Canal 9)
            # Pero intentamos buscar por si acaso
            author_selectors = [
                'span.author',
                'p.author',
                '[class*="author"]',
                'span:contains("Por")'
            ]

            for selector in author_selectors:
                try:
                    if ':contains' in selector:
                        # BeautifulSoup no soporta :contains, usar búsqueda de texto
                        autor_elem = soup.find(text=re.compile(r'^Por\s+'))
                        if autor_elem:
                            details['author'] = autor_elem.strip().replace('Por ', '')
                            break
                    else:
                        autor_elem = soup.select_one(selector)
                        if autor_elem:
                            details['author'] = autor_elem.get_text().strip()
                            break
                except:
                    pass

        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")
            import traceback
            print(traceback.format_exc())

        return details

    def normalizar_fecha_canal9(self, fecha_texto):
        """Normalizar formato de fecha de Canal 9"""
        # Meses en inglés y español
        meses = {
            # Español
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            # Español abreviado
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12,
            # Inglés
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            # Inglés abreviado
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

        try:
            # Limpiar y normalizar el texto
            fecha_limpia = fecha_texto.strip().lower()

            # Remover "hrs" si existe
            fecha_limpia = fecha_limpia.replace(' hrs', '').strip()

            # Dividir en partes
            partes = fecha_limpia.split()

            if len(partes) >= 3:
                # Formato esperado: "30 September 2024"
                dia = int(partes[0])
                mes_nombre = partes[1].lower()
                año = int(partes[2])

                # Buscar el mes en el diccionario
                mes_num = None
                for mes_key, mes_valor in meses.items():
                    if mes_key == mes_nombre or mes_nombre.startswith(mes_key):
                        mes_num = mes_valor
                        break

                if mes_num:
                    # Crear fecha con timezone awareness
                    fecha_resultado = datetime(año, mes_num, dia)
                    # Hacer la fecha timezone-aware
                    fecha_resultado = django_timezone.make_aware(fecha_resultado)
                    print(f"Fecha parseada correctamente: {fecha_texto} -> {fecha_resultado}")
                    return fecha_resultado
                else:
                    print(f"No se pudo encontrar el mes '{mes_nombre}' en el diccionario")

        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")
            print(f"Error parseando fecha: {e}")

        return None
