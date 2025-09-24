from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MinagriScraper(BaseScraper):
    def __init__(self):
        super().__init__('MINAGRI')

    def save_news(self, news_data):
        """Override temporal para asegurar que se guarden las fechas"""
        try:
            from apps.news.models import News
            from django.utils import timezone

            # Verificar longitudes
            if news_data.get('title') and len(news_data['title']) > 500:
                print(f"⚠️ Título excede 500 caracteres ({len(news_data['title'])})")
                news_data['title'] = news_data['title'][:497] + '...'

            # URL ahora soporta 1000 caracteres
            if news_data.get('url') and len(news_data['url']) > 1000:
                print(f"⚠️ URL excede 1000 caracteres ({len(news_data['url'])})")
                news_data['url'] = news_data['url'][:1000]

            # Autor máximo 200 caracteres
            if news_data.get('author') and len(news_data['author']) > 200:
                news_data['author'] = news_data['author'][:197] + '...'

            # Imagen URL
            if not news_data.get('image_url'):
                news_data['image_url'] = ''
            elif len(news_data['image_url']) > 1000:
                news_data['image_url'] = news_data['image_url'][:1000]

            # Convertir fecha naive a aware si es necesario
            if news_data.get('published_date') and timezone.is_naive(news_data['published_date']):
                news_data['published_date'] = timezone.make_aware(news_data['published_date'])

            print(
                f"Procesando: {news_data.get('title', 'Sin título')[:50]}... - Fecha: {news_data.get('published_date')}")

            # Buscar si ya existe
            try:
                news = News.objects.get(url=news_data['url'])
                # Ya existe - actualizar
                updated = False

                # SIEMPRE actualizar fecha si tenemos una y no había antes
                if news_data.get('published_date'):
                    if not news.published_date or news.published_date != news_data['published_date']:
                        news.published_date = news_data['published_date']
                        updated = True
                        print(f"✅ Fecha actualizada: {news_data['published_date']}")

                # Actualizar contenido si es más largo
                if news_data.get('content'):
                    if not news.content or len(news_data['content']) > len(news.content):
                        news.content = news_data['content']
                        news.excerpt = news_data.get('excerpt', '')
                        updated = True
                        print(f"✅ Contenido actualizado: {len(news_data['content'])} caracteres")

                # Actualizar imagen si no teníamos
                if news_data.get('image_url') and news.image_url != news_data['image_url']:
                    news.image_url = news_data['image_url']
                    updated = True

                # Actualizar autor si no teníamos
                if news_data.get('author') and not news.author:
                    news.author = news_data['author']
                    updated = True
                    print(f"✅ Autor actualizado: {news_data['author']}")

                if updated:
                    news.save()
                    print(f"✅ Noticia actualizada: {news_data['title'][:50]}...")
                    return True
                else:
                    print(f"➡️ Sin cambios: {news_data['title'][:50]}...")
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
            print(f"❌ Error guardando/actualizando noticia: {e}")
            print(f"Datos problemáticos: {news_data}")
            import traceback
            print(traceback.format_exc())
            return False

    def get_source_config(self):
        return {
            'base_url': 'https://minagri.gob.cl',
            'search_url': 'https://minagri.gob.cl/?s=pymemad',
            'requires_selenium': True
        }

    def extract_news_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []

        try:
            if self.driver:
                wait = WebDriverWait(self.driver, 30)

                # Esperar que cargue la página
                print("Esperando que carguen los resultados...")
                time.sleep(5)

                # Procesar múltiples páginas
                max_paginas = 3
                pagina_actual = 1

                while pagina_actual <= max_paginas:
                    print(f"Procesando página {pagina_actual}...")

                    # Esperar que carguen los artículos
                    try:
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "elementor-posts-container")))
                    except:
                        print("No se encontró contenedor de posts")
                        break

                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Buscar el contenedor de posts
                    posts_container = soup.find('div', class_='elementor-posts-container')

                    if not posts_container:
                        print("No se encontró contenedor de posts")
                        break

                    # Buscar todos los artículos
                    articulos = posts_container.find_all('article', class_='elementor-post')
                    print(f"Encontrados {len(articulos)} artículos en esta página")

                    for articulo in articulos:
                        noticia = self.extraer_datos_articulo(articulo)
                        if noticia:
                            news_list.append(noticia)
                            print(f"Noticia encontrada: {noticia['title'][:60]}...")

                    # Intentar ir a la siguiente página
                    if pagina_actual < max_paginas:
                        if not self.navegar_siguiente_pagina(pagina_actual + 1):
                            print("No hay más páginas disponibles")
                            break
                        time.sleep(5)

                    pagina_actual += 1

        except Exception as e:
            print(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extraer_datos_articulo(self, articulo):
        """Extraer datos de un artículo específico de MINAGRI"""
        try:
            # Buscar el título y URL
            titulo_elem = articulo.find('h3', class_='elementor-post__title')
            if not titulo_elem:
                return None

            link = titulo_elem.find('a')
            if not link:
                return None

            titulo = link.get_text().strip()
            url = link.get('href', '')

            # Truncar título si excede 500 caracteres
            if len(titulo) > 500:
                print(f"⚠️ Título muy largo ({len(titulo)} chars), truncando...")
                titulo = titulo[:497] + '...'

            # URLField en Django tiene límite default de 200 caracteres
            # Hasta que se actualice el modelo, omitir URLs muy largas
            if len(url) > 200:
                print(f"⚠️ URL muy larga ({len(url)} chars), omitiendo noticia...")
                print(f"   URL: {url[:100]}...")
                # TODO: Actualizar modelo para aumentar max_length de URLField
                return None

            # Solo devolver si tiene título y URL válidos
            if titulo and url:
                return {
                    'title': titulo,
                    'url': url
                }

        except Exception as e:
            print(f"Error extrayendo artículo: {e}")

        return None


    def navegar_siguiente_pagina(self, numero_pagina):
        """Navegar a la siguiente página de resultados"""
        try:
            # Buscar el enlace de paginación
            next_link = self.driver.find_element(
                By.CSS_SELECTOR,
                f"a.page-numbers[href*='page/{numero_pagina}/']"
            )

            if next_link:
                print(f"Navegando a página {numero_pagina}...")
                self.driver.execute_script("arguments[0].click();", next_link)
                return True

        except Exception as e:
            print(f"No se pudo navegar a página {numero_pagina}: {e}")

        return False

    def extract_news_details(self, news_url):
        """
        IMPORTANTE: Solo extraemos contenido adicional.
        El título ya viene de extract_news_list y NO debe ser modificado aquí.
        """
        details = {
            'content': '',
            'excerpt': '',
            'published_date': None,
            'image_url': '',  # Sin imagen por defecto
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

            # EXTRAER CONTENIDO
            contenido = ""

            # El H1 en MINAGRI es el contenido completo, no el título
            titulo_principal = soup.find('h1', class_='post-title')
            if titulo_principal:
                contenido = titulo_principal.get_text().strip()

            # Buscar contenido adicional
            post_body = soup.find('div', class_='post-body')
            if post_body:
                excerpt_div = post_body.find('div', class_='post-excerpt')
                if excerpt_div:
                    texto_adicional = excerpt_div.get_text().strip()
                    if texto_adicional and texto_adicional != contenido:
                        if contenido:
                            contenido += f"\n\n{texto_adicional}"
                        else:
                            contenido = texto_adicional

            # Si no hay contenido aún, buscar en otros selectores
            if not contenido or len(contenido) < 50:
                contenido_selectores = [
                    '.elementor-widget-theme-post-content',
                    '.entry-content',
                    '.post-content',
                    'article .elementor-text-editor'
                ]

                for selector in contenido_selectores:
                    elemento = soup.select_one(selector)
                    if elemento:
                        # Limpiar elementos no deseados
                        for unwanted in elemento.find_all(['script', 'style', 'footer']):
                            unwanted.decompose()

                        texto = elemento.get_text().strip()
                        if texto and len(texto) > len(contenido):
                            contenido = texto
                            break

            # Guardar contenido
            if contenido:
                details['content'] = contenido.strip()
                # Crear excerpt del contenido, no del título
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido
            else:
                # Si no hay contenido, usar un texto por defecto
                details['content'] = 'Contenido no disponible.'
                details['excerpt'] = 'Contenido no disponible.'

            # EXTRAER FECHA - Primero intentar métodos tradicionales
            fecha_elem = soup.find('span', class_='post-date')
            if fecha_elem:
                fecha_span = fecha_elem.find('span', class_='right')
                if fecha_span:
                    fecha_texto = fecha_span.get_text().strip()
                    fecha = self.normalizar_fecha_minagri(fecha_texto)
                    if fecha:
                        details['published_date'] = fecha
                        print(f"Fecha extraída de metadata: {fecha_texto} -> {fecha}")

            # Si no se encuentra fecha, buscar en time elementos
            if not details['published_date']:
                time_elem = soup.find('time')
                if time_elem:
                    if time_elem.get('datetime'):
                        fecha = self.parse_datetime_iso(time_elem.get('datetime'))
                        if fecha:
                            details['published_date'] = fecha
                    else:
                        fecha_texto = time_elem.get_text().strip()
                        fecha = self.normalizar_fecha_minagri(fecha_texto)
                        if fecha:
                            details['published_date'] = fecha

            # NUEVO: Si no se encontró fecha, buscarla en el contenido
            if not details['published_date'] and contenido:
                # Buscar patrón: "14 de mayo de 2019.-" o similar
                import re
                # Patrón para fechas en formato "DD de MES de AAAA"
                patron_fecha = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\.-'
                match = re.search(patron_fecha, contenido)

                if match:
                    dia = int(match.group(1))
                    mes_nombre = match.group(2).lower()
                    año = int(match.group(3))

                    # Convertir usando la función existente
                    fecha_texto = f"{dia} {mes_nombre}, {año}"
                    fecha = self.normalizar_fecha_minagri(fecha_texto)
                    if fecha:
                        details['published_date'] = fecha
                        print(f"Fecha extraída del contenido: {match.group(0)} -> {fecha}")

            # NO BUSCAR IMAGEN - dejar vacío como indicaste
            details['image_url'] = ''

            # EXTRAER AUTOR
            autor_elem = soup.find('span', class_='post-author')
            if autor_elem:
                autor_link = autor_elem.find('a')
                if autor_link:
                    details['author'] = autor_link.get_text().strip()

            # Si no hay autor, extraer tipo del artículo
            if not details['author']:
                article = soup.find('article')
                if article:
                    clases = article.get('class', [])

                    if 'type-agenda_autoridades' in clases:
                        details['author'] = 'Agenda Autoridades'
                    elif 'type-noticia' in clases:
                        details['author'] = 'Noticia'
                    elif 'type-post' in clases:
                        details['author'] = 'Post'
                    else:
                        details['author'] = 'MINAGRI'

            print(
                f"Detalles extraídos - Contenido: {len(details['content'])} chars, Fecha: {details['published_date']}")

        except Exception as e:
            print(f"Error extrayendo detalles de {news_url}: {e}")
            import traceback
            print(traceback.format_exc())

        return details

    def parse_datetime_iso(self, datetime_str):
        """Parsear fecha en formato ISO"""
        try:
            if 'T' in datetime_str:
                fecha_parte = datetime_str.split('T')[0]
                año, mes, dia = fecha_parte.split('-')
                return datetime(int(año), int(mes), int(dia))
        except Exception as e:
            print(f"Error parseando datetime ISO '{datetime_str}': {e}")
        return None

    def normalizar_fecha_minagri(self, fecha_texto):
        """Normalizar formato de fecha de MINAGRI"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        try:
            # Formato: "24 enero, 2019"
            fecha_limpia = fecha_texto.strip()
            fecha_limpia = fecha_limpia.replace(',', '')

            # Dividir en partes
            partes = fecha_limpia.split()

            if len(partes) >= 3:
                dia = int(partes[0])
                mes_nombre = partes[1].lower()
                año = int(partes[2])

                mes_num = meses.get(mes_nombre, None)
                if mes_num:
                    return datetime(año, mes_num, dia)

            # Intentar otro formato: "24 de enero de 2019"
            if ' de ' in fecha_texto:
                fecha_limpia = fecha_texto.replace(' de ', ' ')
                partes = fecha_limpia.split()

                if len(partes) >= 3:
                    dia = int(partes[0])
                    mes_nombre = partes[1].lower()
                    año = int(partes[2])

                    mes_num = meses.get(mes_nombre, None)
                    if mes_num:
                        return datetime(año, mes_num, dia)

        except Exception as e:
            print(f"Error normalizando fecha '{fecha_texto}': {e}")

        return None
