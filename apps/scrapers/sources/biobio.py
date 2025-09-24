from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from apps.scrapers.base import BaseScraper


class BioBioScraper(BaseScraper):
    def __init__(self):
        super().__init__('Radio Bio Bio')
        self._news_list_cache = []

    def get_source_config(self):
        return {
            'base_url': 'https://www.biobiochile.cl',
            'search_url': 'https://www.biobiochile.cl/buscador.shtml?s=pymemad',
            'requires_selenium': True
        }

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

                # Actualizar imagen si es diferente
                if news_data.get('image_url') and news.image_url != news_data['image_url']:
                    news.image_url = news_data['image_url']
                    updated = True
                    print(f"Imagen actualizada: {news_data['image_url']}")

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

    def extract_news_list(self, html_content):
        """Extrae solo la lista básica de noticias con título, URL y fecha"""
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []

        try:
            if self.driver:
                wait = WebDriverWait(self.driver, 20)
                time.sleep(8)

                # Procesar hasta 3 páginas de resultados
                max_paginas = 3
                pagina_actual = 1

                while pagina_actual <= max_paginas:
                    print(f"Procesando página {pagina_actual}...")

                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".results-container")))
                        print("Contenedor de resultados cargado")
                    except:
                        self.logger.warning("Timeout esperando resultados")

                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Buscar elementos de noticias
                    elementos_encontrados = []

                    # Buscar en el contenedor principal de resultados
                    section_body = soup.select_one('.section-buscador .section-body')
                    if section_body:
                        print("Section-body encontrado")

                        # Buscar todos los links que contienen artículos
                        links_con_articulos = section_body.select('a[href*="/noticias/"]')

                        for link in links_con_articulos:
                            articulo = link.find('article', class_='article')
                            if articulo:
                                clases_parent = ' '.join(link.get('class', []))
                                clases_articulo = ' '.join(articulo.get('class', []))

                                if 'd-none' not in clases_parent and 'd-none' not in clases_articulo:
                                    elementos_encontrados.append(link)

                        print(f"Encontrados {len(elementos_encontrados)} elementos válidos")

                    # Si no encuentra nada, buscar directamente los artículos
                    if not elementos_encontrados:
                        print("Usando estrategia alternativa...")
                        articulos_directos = soup.select('article.article-horizontal')

                        for articulo in articulos_directos:
                            parent = articulo.find_parent()
                            if parent:
                                parent_classes = ' '.join(parent.get('class', []))
                                if ('nav-menu' not in parent_classes and
                                        'd-none' not in parent_classes and
                                        'navbar' not in parent_classes):
                                    link_padre = articulo.find_parent('a')
                                    if link_padre and '/noticias/' in link_padre.get('href', ''):
                                        elementos_encontrados.append(link_padre)

                    # Procesar elementos encontrados
                    if elementos_encontrados:
                        print(f"Procesando {len(elementos_encontrados)} elementos...")

                        for elemento in elementos_encontrados:
                            noticia = self.extraer_datos_basicos(elemento)
                            if noticia and not any(n['url'] == noticia['url'] for n in news_list):
                                news_list.append(noticia)
                                print(f"Noticia encontrada: {noticia['title'][:60]}...")

                    # Intentar cargar más resultados
                    if pagina_actual < max_paginas:
                        try:
                            boton_mas = self.driver.find_element(By.CSS_SELECTOR, ".fetch-btn")
                            if boton_mas.is_displayed() and boton_mas.is_enabled():
                                print("Cargando más resultados...")
                                self.driver.execute_script("arguments[0].click();", boton_mas)
                                time.sleep(5)
                                pagina_actual += 1
                            else:
                                break
                        except:
                            print("No hay más resultados para cargar")
                            break
                    else:
                        break

        except Exception as e:
            print(f"Error extrayendo lista de noticias: {e}")
            import traceback
            print(traceback.format_exc())

        # Guardar en cache para acceso posterior
        self._news_list_cache = news_list
        return news_list

    def extraer_datos_basicos(self, elemento):
        """Extraer solo datos básicos de la lista (título, URL, fecha)"""
        try:
            if elemento.name == 'a':
                link_elem = elemento
                articulo = elemento.find('article')
            else:
                link_elem = elemento.find_parent('a') or elemento.find('a')
                articulo = elemento.find('article') or elemento

            # Extraer URL
            url = ""
            if link_elem and link_elem.get('href'):
                url = link_elem.get('href')
                if url.startswith('/'):
                    url = 'https://www.biobiochile.cl' + url
                elif url.startswith('http://'):
                    url = url.replace('http://', 'https://')

            # Extraer título
            titulo = ""
            titulo_elem = articulo.find('h2', class_='article-title') if articulo else None
            if titulo_elem:
                titulo = titulo_elem.get_text().strip()

            # Extraer fecha y parsearla inmediatamente
            fecha_parseada = None
            fecha_elem = articulo.find('div', class_='article-date-hour') if articulo else None
            if fecha_elem:
                fecha_texto = fecha_elem.get_text()
                fecha_texto = ' '.join(fecha_texto.split()).strip()
                print(f"Fecha encontrada: {fecha_texto}")
                fecha_parseada = self.parsear_fecha_desde_texto(fecha_texto)

            if titulo and url and 'biobiochile.cl' in url:
                return {
                    'title': titulo,
                    'url': url,
                    'published_date': fecha_parseada  # Ya parseada
                }

        except Exception as e:
            print(f"Error al extraer datos básicos: {e}")

        return None

    def extract_news_details(self, news_url):
        """Extraer contenido completo de la noticia"""
        details = {
            'content': '',
            'excerpt': '',
            'published_date': None,
            'image_url': '',
            'author': ''
        }

        try:
            print(f"Obteniendo contenido de: {news_url}")

            # Primero buscar si ya tenemos la fecha en el cache
            for item in self._news_list_cache:
                if item.get('url') == news_url and item.get('published_date'):
                    details['published_date'] = item['published_date']
                    print(f"Fecha recuperada del cache: {details['published_date']}")
                    break

            # Navegar a la página
            self.driver.get(news_url)
            time.sleep(3)  # Esperar menos tiempo

            # Obtener el HTML
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Si no tenemos fecha, buscarla en la página
            if not details['published_date']:
                fecha_elem = soup.find('div', class_='article-date-hour')
                if fecha_elem:
                    fecha_texto = ' '.join(fecha_elem.get_text().split()).strip()
                    details['published_date'] = self.parsear_fecha_desde_texto(fecha_texto)

            # Buscar contenido principal
            contenido = ""

            # Buscar en post-content primero
            post_content = soup.find('div', class_='post-content')
            if post_content:
                # Extraer párrafos directamente sin limpieza
                paragraphs = post_content.find_all('p')
                contenido_parrafos = []

                for p in paragraphs:
                    texto = p.get_text().strip()
                    if texto and len(texto) > 20:
                        contenido_parrafos.append(texto)

                if contenido_parrafos:
                    contenido = '\n\n'.join(contenido_parrafos[:20])  # Limitar a 20 párrafos
                    print(f"Contenido extraído de post-content: {len(contenido)} caracteres")

            # Si no hay contenido suficiente, buscar alternativas
            if not contenido or len(contenido) < 100:
                # Buscar en el artículo principal
                article = soup.find('article') or soup.find('main')
                if article:
                    paragraphs = article.find_all('p')
                    contenido_alt = []
                    for p in paragraphs[:15]:
                        texto = p.get_text().strip()
                        if texto and len(texto) > 20:
                            contenido_alt.append(texto)

                    if contenido_alt:
                        contenido = '\n\n'.join(contenido_alt)
                        print(f"Contenido extraído de article/main: {len(contenido)} caracteres")

            # Guardar contenido
            if contenido:
                details['content'] = contenido[:5000]  # Limitar a 5000 caracteres
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido

            # Buscar imagen
            # Primero en post-image con background-image
            post_image = soup.find('div', class_='post-image')
            if post_image:
                style = post_image.get('style', '')
                if style and 'background-image' in style:
                    # Extraer URL del estilo background-image: url(...)
                    match = re.search(r'background-image:\s*url\((.*?)\)', style)
                    if match:
                        img_url = match.group(1).strip('"\'')
                        if img_url:
                            details['image_url'] = img_url
                            print(f"Imagen encontrada en background-image: {img_url}")

            # Si no encontramos en background-image, buscar en tags img
            if not details['image_url']:
                # Buscar primero en post-image > a > img
                if post_image:
                    img_link = post_image.find('a')
                    if img_link:
                        img = img_link.find('img')
                        if img and img.get('src'):
                            details['image_url'] = img.get('src')
                            print(f"Imagen encontrada en post-image > a > img: {details['image_url']}")

                # Si aún no hay imagen, buscar cualquier img con biobiochile
                if not details['image_url']:
                    img = soup.find('img', src=re.compile(r'biobiochile'))
                    if img:
                        details['image_url'] = img.get('src', '')
                        print(f"Imagen encontrada en img tag: {details['image_url']}")

            print(f"Contenido obtenido: {len(details['content'])} caracteres")

        except Exception as e:
            print(f"Error obteniendo contenido de {news_url}: {e}")
            # Si tenemos fecha, al menos devolver eso
            if details.get('published_date'):
                print("Devolviendo al menos la fecha")

        return details

    def parsear_fecha_desde_texto(self, fecha_texto):
        """Parsear fecha desde el texto"""
        try:
            if '|' in fecha_texto:
                partes = fecha_texto.split('|')
                fecha_str = partes[0].strip()
                hora_str = partes[1].strip() if len(partes) > 1 else ""

                fecha_normalizada = self.normalizar_fecha_biobio(fecha_str)
                if fecha_normalizada and hora_str:
                    try:
                        hora_partes = hora_str.split(':')
                        if len(hora_partes) == 2:
                            hora = int(hora_partes[0])
                            minuto = int(hora_partes[1])
                            fecha_normalizada = fecha_normalizada.replace(hour=hora, minute=minuto)
                    except:
                        pass

                return fecha_normalizada
            else:
                return self.normalizar_fecha_biobio(fecha_texto)
        except Exception as e:
            print(f"Error parseando fecha {fecha_texto}: {e}")

        return None

    def normalizar_fecha_biobio(self, fecha_texto):
        """Normalizar formato de fecha de Bio Bio"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        try:
            # Remover día de la semana y comas
            fecha_limpia = re.sub(r'^[a-záéíóú]+\s+', '', fecha_texto.lower(), flags=re.IGNORECASE)
            fecha_limpia = fecha_limpia.replace(',', '')

            partes = fecha_limpia.strip().split()
            if len(partes) >= 3:
                dia = int(partes[0])
                mes_nombre = partes[1].lower()
                año = int(partes[2])

                for mes_key, mes_num in meses.items():
                    if mes_key in mes_nombre:
                        return datetime(año, mes_num, dia)
        except Exception as e:
            print(f"Error normalizando fecha {fecha_texto}: {e}")

        return None
