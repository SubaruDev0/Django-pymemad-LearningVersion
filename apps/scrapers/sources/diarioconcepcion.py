from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DiarioConcepcionScraper(BaseScraper):
    def __init__(self):
        super().__init__('Diario Concepción')
        self._news_list_cache = []

    def get_source_config(self):
        return {
            'base_url': 'https://www.diarioconcepcion.cl',
            'search_url': 'https://www.diarioconcepcion.cl/search?s=pymemad',
            'requires_selenium': True
        }

    def save_news(self, news_data):
        """Override para actualizar noticias existentes con mejor logging"""
        try:
            from apps.news.models import News

            # Logging detallado de entrada
            print("=" * 60)
            print(f"📰 Procesando noticia:")
            print(f"   Título: {news_data.get('title', 'Sin título')}")
            print(f"   URL: {news_data.get('url', 'Sin URL')}")
            print(f"   Fecha: {news_data.get('published_date', 'Sin fecha')}")
            print(f"   Contenido: {len(news_data.get('content', ''))} caracteres")
            print(f"   Imagen: {'Sí' if news_data.get('image_url') else 'No'}")

            # Buscar si ya existe
            try:
                news = News.objects.get(url=news_data['url'])
                print(f"⚠️  Noticia YA EXISTE en BD")

                # Ya existe - verificar qué campos actualizar
                updated = False
                updates = []

                # Comparar y actualizar fecha
                if news_data.get('published_date'):
                    if news.published_date != news_data['published_date']:
                        old_date = news.published_date
                        news.published_date = news_data['published_date']
                        updated = True
                        updates.append(f"Fecha: {old_date} → {news_data['published_date']}")
                    else:
                        print(f"   Fecha sin cambios: {news.published_date}")

                # Comparar y actualizar contenido
                if news_data.get('content'):
                    old_len = len(news.content) if news.content else 0
                    new_len = len(news_data['content'])

                    if not news.content or new_len > old_len:
                        news.content = news_data['content']
                        news.excerpt = news_data.get('excerpt', '')
                        updated = True
                        updates.append(f"Contenido: {old_len} → {new_len} caracteres")
                    else:
                        print(f"   Contenido sin cambios: {old_len} caracteres")

                # Comparar y actualizar imagen
                if news_data.get('image_url'):
                    if news.image_url != news_data['image_url']:
                        old_img = news.image_url or 'Sin imagen'
                        news.image_url = news_data['image_url']
                        updated = True
                        updates.append(f"Imagen actualizada")
                    else:
                        print(f"   Imagen sin cambios")

                if updated:
                    news.save()
                    print(f"✅ ACTUALIZADA - Cambios realizados:")
                    for update in updates:
                        print(f"   - {update}")
                    return True
                else:
                    print(f"ℹ️  SIN CAMBIOS - Noticia ya está actualizada")
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
                print(f"✅ NUEVA NOTICIA CREADA")
                print(f"   ID: {news.id}")
                print(f"   Guardada con {len(news.content)} caracteres de contenido")
                return True

        except Exception as e:
            self.logger.error(f"❌ ERROR guardando/actualizando noticia:")
            self.logger.error(f"   Error: {e}")
            self.logger.error(f"   URL: {news_data.get('url', 'Sin URL')}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        finally:
            print("=" * 60)

    def extract_news_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []

        try:
            if self.driver:
                wait = WebDriverWait(self.driver, 30)

                # Esperar que cargue la página
                print("Esperando que carguen los resultados...")
                time.sleep(5)

                # Configuración de paginación
                max_paginas = 50
                pagina_actual = 1
                paginas_sin_resultados = 0

                while pagina_actual <= max_paginas and paginas_sin_resultados < 3:
                    print(f"Procesando página {pagina_actual}...")

                    # Esperar la lista principal
                    try:
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "l-list")))
                    except:
                        self.logger.warning("No se encontró la lista de noticias")
                        paginas_sin_resultados += 1
                        if paginas_sin_resultados >= 3:
                            break
                        # Intentar navegar a la siguiente página de todas formas
                        if self.navegar_siguiente_pagina():
                            pagina_actual += 1
                            continue
                        else:
                            break

                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Extraer noticias de la página actual
                    noticias_pagina = self.extraer_noticias_de_pagina(soup)

                    if not noticias_pagina:
                        print(f"No hay noticias en la página {pagina_actual}")
                        paginas_sin_resultados += 1
                    else:
                        print(f"Página {pagina_actual}: {len(noticias_pagina)} noticias encontradas")
                        news_list.extend(noticias_pagina)
                        paginas_sin_resultados = 0  # Resetear contador si encontramos noticias

                    # Intentar ir a la siguiente página
                    if not self.navegar_siguiente_pagina():
                        print("No se puede navegar a más páginas")
                        break

                    pagina_actual += 1
                    time.sleep(3)

                # Guardar en cache
                self._news_list_cache = news_list
                print(f"Total de noticias extraídas: {len(news_list)}")
                print(f"Páginas procesadas: {pagina_actual}")

        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return news_list

    def extraer_noticias_de_pagina(self, soup):
        """Extraer noticias de la página actual"""
        noticias = []

        # Buscar la lista principal
        lista = soup.find('div', class_='l-list')

        if not lista:
            self.logger.warning("No se encontró la lista de noticias")
            return noticias

        # Buscar todos los items
        items = lista.find_all('div', class_='l-list__item')

        # Filtrar solo los que tienen la clase main-headline
        items_noticia = [item for item in items if 'main-headline' in item.get('class', [])]

        # Verificar si el primer item es el título de búsqueda
        if items_noticia and items_noticia[0].find('h1', string=re.compile(r'Búsqueda por:')):
            items_noticia = items_noticia[1:]  # Excluir el título

        print(f"Encontrados {len(items_noticia)} artículos")

        for i, item in enumerate(items_noticia):
            noticia = self.extraer_datos_noticia(item)
            if noticia:
                noticias.append(noticia)
                self.logger.debug(f"Noticia {i + 1}: {noticia['title'][:60]}...")

        return noticias

    def navegar_siguiente_pagina(self):
        """Navegar a la siguiente página de resultados"""
        try:
            # Primero intentar encontrar la paginación actual
            current_url = self.driver.current_url

            # Método 1: Modificar directamente la URL con el parámetro de página
            if 'page=' in current_url:
                # Extraer el número de página actual
                match = re.search(r'page=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page = current_page + 1
                    next_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
                    print(f"Navegando a página {next_page} mediante URL")
                    self.driver.get(next_url)
                    time.sleep(4)

                    # Verificar si hay resultados en la nueva página
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    if self.hay_resultados_en_pagina(soup):
                        return True
                    else:
                        print("No hay más resultados en la siguiente página")
                        return False
            else:
                # Si no hay parámetro page, agregarlo
                separator = '&' if '?' in current_url else '?'
                next_url = f"{current_url}{separator}page=2"
                print("Agregando parámetro page=2 a la URL")
                self.driver.get(next_url)
                time.sleep(4)

                # Verificar si hay resultados
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                if self.hay_resultados_en_pagina(soup):
                    return True

            # Método 2: Buscar enlaces de paginación en el HTML
            pagination_selectors = [
                "a.pagination__next",
                "a.next",
                ".pagination a",
                "a[rel='next']",
                ".page-numbers",
                ".pager a",
                "a[href*='page=']"
            ]

            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        # Verificar si es un enlace a la siguiente página
                        href = elem.get_attribute('href')
                        texto = elem.get_text().strip().lower()

                        if href and (
                                'page=' in href or any(x in texto for x in ['siguiente', 'next', '»', '→', 'sig'])):
                            if elem.is_displayed() and elem.is_enabled():
                                print(f"Clic en enlace de paginación: {texto or href}")
                                self.driver.execute_script("arguments[0].click();", elem)
                                time.sleep(4)
                                return True
                except Exception as e:
                    self.logger.debug(f"Error con selector {selector}: {str(e)}")
                    continue

            # Método 3: Buscar números de página y hacer clic en el siguiente
            try:
                # Buscar todos los elementos que parecen números de página
                page_numbers = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='page=']")
                current_page_num = self.obtener_pagina_actual()

                for elem in page_numbers:
                    try:
                        page_text = elem.get_text().strip()
                        if page_text.isdigit():
                            page_num = int(page_text)
                            if page_num == current_page_num + 1:
                                print(f"Navegando a página {page_num}")
                                self.driver.execute_script("arguments[0].click();", elem)
                                time.sleep(4)
                                return True
                    except:
                        continue
            except:
                pass

            # Método 4: Scroll infinito
            print("Intentando scroll infinito...")
            for i in range(3):  # Intentar scroll varias veces
                old_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = self.driver.execute_script("return document.body.scrollHeight")

                if new_height > old_height:
                    print("Cargadas más noticias mediante scroll")
                    return True

            print("No se encontró forma de navegar a la siguiente página")
            return False

        except Exception as e:
            self.logger.error(f"Error navegando a siguiente página: {str(e)}")
            return False

    def obtener_pagina_actual(self):
        """Obtener el número de página actual desde la URL"""
        try:
            current_url = self.driver.current_url
            if 'page=' in current_url:
                match = re.search(r'page=(\d+)', current_url)
                if match:
                    return int(match.group(1))
            return 1
        except:
            return 1

    def hay_resultados_en_pagina(self, soup):
        """Verificar si hay resultados de búsqueda en la página"""
        # Buscar la lista de resultados
        lista = soup.find('div', class_='l-list')
        if not lista:
            return False

        # Buscar items de noticia (excluyendo el título de búsqueda)
        items = lista.find_all('div', class_='l-list__item')
        items_noticia = [item for item in items if 'main-headline' in item.get('class', [])]

        # Filtrar el título de búsqueda si existe
        if items_noticia and items_noticia[0].find('h1', string=re.compile(r'Búsqueda por:')):
            items_noticia = items_noticia[1:]

        return len(items_noticia) > 0

    def extraer_datos_noticia(self, item):
        """Extraer datos de una noticia específica"""
        try:
            # Buscar el título y URL
            titulo_elem = item.find('h1', class_='main-headline__title')
            if not titulo_elem:
                return None

            link = titulo_elem.find('a')
            if not link:
                return None

            titulo = link.get_text().strip()
            url = link.get('href', '')

            # Asegurar URL completa
            if not url.startswith('http'):
                url = urljoin('https://www.diarioconcepcion.cl', url)

            # Extraer fecha
            fecha_parseada = None
            fecha_elem = item.find('small', class_='main-headline__category')
            if fecha_elem:
                fecha_texto = fecha_elem.get_text().strip()
                print(f"Fecha encontrada: {fecha_texto}")
                fecha_parseada = self.normalizar_fecha(fecha_texto)
                if fecha_parseada:
                    print(f"Fecha parseada: {fecha_parseada}")

            # Extraer descripción
            descripcion = ""
            desc_elem = item.find('div', class_='main-headline__text')
            if desc_elem:
                p = desc_elem.find('p')
                if p:
                    descripcion = p.get_text().strip()

            # Extraer imagen
            imagen_url = ""
            img_container = item.find('div', class_='main-headline__image')
            if img_container:
                img = img_container.find('img')
                if img:
                    imagen_url = img.get('src', '')
                    # Manejar lazy loading
                    if not imagen_url or 'lazy' in img.get('class', []):
                        imagen_url = img.get('data-src', imagen_url)

                    if imagen_url and not imagen_url.startswith('http'):
                        imagen_url = urljoin('https://www.diarioconcepcion.cl', imagen_url)

            # Devolver datos de la noticia
            resultado = {
                'title': titulo,
                'url': url,
                'published_date': fecha_parseada
            }

            # Agregar campos opcionales si existen
            if descripcion:
                resultado['excerpt'] = descripcion
            if imagen_url:
                resultado['image_url'] = imagen_url

            return resultado

        except Exception as e:
            self.logger.error(f"Error extrayendo noticia: {str(e)}")
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
            print("-" * 60)
            print(f"🔍 Extrayendo detalles de noticia:")
            print(f"   URL: {news_url}")

            # Primero buscar si ya tenemos datos en el cache
            cached_data = False
            for item in self._news_list_cache:
                if item.get('url') == news_url:
                    if item.get('published_date'):
                        details['published_date'] = item['published_date']
                        print(f"   📅 Fecha del cache: {details['published_date']}")
                        cached_data = True
                    if item.get('excerpt'):
                        details['excerpt'] = item['excerpt']
                        print(f"   📝 Excerpt del cache: {len(item['excerpt'])} caracteres")
                        cached_data = True
                    if item.get('image_url'):
                        details['image_url'] = item['image_url']
                        print(f"   🖼️  Imagen del cache: {item['image_url'][:50]}...")
                        cached_data = True
                    break

            if not cached_data:
                print("   ℹ️  No hay datos en cache para esta noticia")

            print(f"   🌐 Navegando a la página...")
            self.driver.get(news_url)
            time.sleep(3)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Buscar contenido principal - estructura específica de Diario Concepción
            contenido = ""

            # Primero buscar en the-single__text que es donde está el contenido principal
            contenido_elem = soup.find('div', class_='the-single__text')
            if contenido_elem:
                print("Encontrado div.the-single__text")

                # Crear una copia para no modificar el original
                contenido_copy = contenido_elem.__copy__()

                # Eliminar solo elementos de publicidad y scripts
                for script in contenido_copy.find_all('script'):
                    script.decompose()
                for style in contenido_copy.find_all('style'):
                    style.decompose()

                # Eliminar divs de publicidad específicos
                for ad_div in contenido_copy.find_all('div', class_='rtb_slot'):
                    ad_div.decompose()
                for ad_div in contenido_copy.find_all('div', class_='aside-banner'):
                    ad_div.decompose()

                # Ahora extraer TODO el texto de los párrafos
                paragrafos = contenido_copy.find_all('p')
                print(f"Encontrados {len(paragrafos)} párrafos")

                contenido_parrafos = []
                for i, p in enumerate(paragrafos):
                    texto = p.get_text().strip()
                    if texto and len(texto) > 10:  # Reducir el límite mínimo
                        contenido_parrafos.append(texto)
                        self.logger.debug(f"Párrafo {i + 1} ({len(texto)} chars): {texto[:50]}...")

                if contenido_parrafos:
                    contenido = '\n\n'.join(contenido_parrafos)
                    print(
                        f"Contenido total extraído: {len(contenido)} caracteres, {len(contenido_parrafos)} párrafos")
                else:
                    self.logger.warning("No se encontraron párrafos válidos")

            # Si no encontramos suficiente contenido, intentar método alternativo
            if not contenido or len(contenido) < 100:
                print("Intentando método alternativo para extraer contenido")

                # Buscar todo el artículo
                article_container = soup.find('div', class_='the-single')
                if article_container:
                    # Buscar div con el texto
                    text_div = article_container.find('div', class_='the-single__text')
                    if text_div:
                        # Obtener todo el contenido HTML y procesarlo
                        all_paragraphs = []

                        # Buscar todos los elementos que contienen texto
                        for elem in text_div.descendants:
                            if elem.name == 'p' and elem.string:
                                text = elem.get_text().strip()
                                if text and len(text) > 10:
                                    all_paragraphs.append(text)

                        if all_paragraphs:
                            contenido = '\n\n'.join(all_paragraphs)
                            print(f"Método alternativo: {len(all_paragraphs)} párrafos encontrados")

            # Si aún no tenemos contenido suficiente, último intento
            if not contenido or len(contenido) < 100:
                print("Último intento: extrayendo todos los párrafos del body")
                # Buscar todos los párrafos en el body que parezcan contenido
                all_p = soup.find_all('p')
                content_paragraphs = []

                for p in all_p:
                    # Verificar que el párrafo esté dentro de un contenedor de contenido
                    parent = p.parent
                    parent_classes = ' '.join(parent.get('class', [])) if parent else ''

                    # Evitar párrafos de navegación, footer, etc.
                    if any(skip in parent_classes for skip in ['nav', 'footer', 'header', 'menu']):
                        continue

                    texto = p.get_text().strip()
                    # Solo párrafos con contenido sustancial
                    if texto and len(texto) > 30 and not any(skip in texto.lower() for skip in
                                                             ['compartir', 'facebook', 'twitter', 'whatsapp', 'cookies',
                                                              'publicidad']):
                        content_paragraphs.append(texto)

                if content_paragraphs:
                    contenido = '\n\n'.join(content_paragraphs[:30])  # Limitar a 30 párrafos
                    print(f"Último intento: {len(content_paragraphs)} párrafos encontrados")

            # Guardar contenido
            if contenido:
                # No limitar a 5000 caracteres todavía, ver cuánto contenido tenemos
                print(f"Contenido final: {len(contenido)} caracteres")
                details['content'] = contenido[:10000]  # Aumentar límite a 10000
                # Solo actualizar excerpt si no lo teníamos del cache
                if not details['excerpt']:
                    details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido
            else:
                self.logger.warning("No se pudo extraer contenido de la noticia")

            # Buscar fecha solo si no la tenemos del cache
            if not details['published_date']:
                # Primero buscar en the-single__date
                fecha_elem = soup.find('span', class_='the-single__date')
                if fecha_elem:
                    fecha_texto = fecha_elem.get_text().strip()
                    fecha_parseada = self.normalizar_fecha(fecha_texto)
                    if fecha_parseada:
                        details['published_date'] = fecha_parseada
                else:
                    # Buscar alternativa
                    fecha_elem = soup.find('small', class_='main-headline__category')
                    if fecha_elem:
                        fecha_texto = fecha_elem.get_text().strip()
                        fecha_parseada = self.normalizar_fecha(fecha_texto)
                        if fecha_parseada:
                            details['published_date'] = fecha_parseada

            # Buscar imagen solo si no la tenemos del cache
            if not details['image_url']:
                # Primero buscar en figure.the-single__image
                figure = soup.find('figure', class_='the-single__image')
                if figure:
                    img = figure.find('img')
                    if img and img.get('src'):
                        details['image_url'] = img.get('src')
                        print(f"Imagen encontrada: {details['image_url']}")

                # Si no, buscar alternativas
                if not details['image_url']:
                    img_selectors = [
                        'img[src*="diarioconcepcion"]',
                        'img[src*="assets.diarioconcepcion"]',
                        '.post-image img',
                        '.article-image img',
                        'img[class*="article"]'
                    ]

                    for selector in img_selectors:
                        img_elem = soup.select_one(selector)
                        if img_elem and img_elem.get('src'):
                            src = img_elem.get('src', '')
                            if not src.startswith('http'):
                                src = urljoin(news_url, src)
                            details['image_url'] = src
                            break

            # Buscar autor
            autor_elem = soup.find('span', class_='the-single__author')
            if autor_elem:
                # Buscar el link dentro del span
                autor_link = autor_elem.find('a')
                if autor_link:
                    details['author'] = autor_link.get_text().strip()
                else:
                    # Si no hay link, limpiar el texto
                    texto_autor = autor_elem.get_text()
                    # Remover "Por:" del texto
                    texto_autor = texto_autor.replace('Por:', '').strip()
                    if texto_autor:
                        details['author'] = texto_autor

                if details['author']:
                    print(f"   👤 Autor encontrado: {details['author']}")

            # Resumen final
            print(f"   📊 Resumen de extracción:")
            print(f"      - Contenido: {len(details['content'])} caracteres")
            print(f"      - Fecha: {details['published_date'] or 'No encontrada'}")
            print(f"      - Imagen: {'Sí' if details['image_url'] else 'No'}")
            print(f"      - Autor: {details['author'] or 'No encontrado'}")
            print("-" * 60)

        except Exception as e:
            self.logger.error(f"❌ Error extrayendo detalles de {news_url}")
            self.logger.error(f"   Error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            print("-" * 60)

        return details

    def normalizar_fecha(self, fecha_texto):
        """Normalizar formato de fecha de Diario Concepción"""
        # Formato: "23 de marzo 2025"
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        try:
            # Limpiar y dividir
            fecha_limpia = fecha_texto.lower().replace(' de ', ' ')
            partes = fecha_limpia.split()

            if len(partes) >= 3:
                dia = int(partes[0])
                mes_nombre = partes[1]
                año = int(partes[2])

                if mes_nombre in meses:
                    mes = meses[mes_nombre]
                    return datetime(año, mes, dia)
        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")

        return None

    def scrape(self):
        """Override del método scrape para agregar logging detallado"""
        print("🚀 INICIANDO SCRAPING DIARIO CONCEPCIÓN - PYMEMAD")
        print("=" * 60)

        # Llamar al método padre
        result = super().scrape()

        # Mostrar resumen final
        print("=" * 60)
        print("📊 RESUMEN FINAL DEL SCRAPING:")

        if hasattr(self, 'scraping_log') and self.scraping_log:
            print(f"   - Noticias encontradas: {self.scraping_log.news_found}")
            print(f"   - Noticias guardadas/actualizadas: {self.scraping_log.news_saved}")
            print(f"   - Estado: {self.scraping_log.status}")

            if self.scraping_log.news_saved > 0:
                print(f"   ✅ Éxito: {self.scraping_log.news_saved} noticias procesadas")
            else:
                print(f"   ⚠️  Advertencia: No se guardaron noticias nuevas")

        print("=" * 60)
        print("✅ SCRAPING COMPLETADO")

        return result
