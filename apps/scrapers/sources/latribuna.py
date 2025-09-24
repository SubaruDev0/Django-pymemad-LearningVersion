from apps.scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LatribunaScraper(BaseScraper):
    def __init__(self):
        super().__init__('La Tribuna')

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
            'base_url': 'https://www.latribuna.cl',
            'search_url': 'https://www.latribuna.cl/buscador/?search=Pymemad',
            'requires_selenium': True
        }

    def extract_news_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []

        try:
            if self.driver:
                wait = WebDriverWait(self.driver, 30)

                # Esperar más tiempo inicial para que carguen los resultados
                print("Esperando que carguen los resultados iniciales...")
                time.sleep(15)

                # Esperar a que aparezca el contenedor de resultados
                wait.until(EC.presence_of_element_located((By.ID, "Result")))
                print("Contenedor de resultados cargado")

                urls_procesadas = set()  # Para evitar duplicados
                carga_actual = 1
                max_cargas = 5
                cargas_sin_nuevas_noticias = 0

                while carga_actual <= max_cargas and cargas_sin_nuevas_noticias < 3:
                    print(f"Procesando carga {carga_actual}...")

                    # Esperar un poco antes de procesar
                    time.sleep(3)

                    # Obtener HTML actualizado
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Buscar el contenedor de resultados
                    result_container = soup.select_one('#Result')

                    if not result_container:
                        self.logger.warning("No se encontró contenedor #Result")
                        break

                    # Buscar todos los artículos
                    articulos = result_container.find_all('article', class_='post-main__post')
                    print(f"Encontrados {len(articulos)} artículos en esta carga")

                    # Contar noticias nuevas en esta carga
                    noticias_nuevas_carga = 0
                    for articulo in articulos:
                        noticia = self.extraer_datos_articulo(articulo)
                        if noticia and noticia['url'] not in urls_procesadas:
                            urls_procesadas.add(noticia['url'])
                            news_list.append(noticia)
                            noticias_nuevas_carga += 1
                            print(f"Noticia encontrada: {noticia['title'][:60]}...")

                    print(f"Carga {carga_actual}: {noticias_nuevas_carga} noticias nuevas de {len(articulos)} totales")

                    # Si no encontró noticias nuevas, contar
                    if noticias_nuevas_carga == 0:
                        cargas_sin_nuevas_noticias += 1
                        print(f"Sin noticias nuevas en esta carga ({cargas_sin_nuevas_noticias}/3)")
                    else:
                        cargas_sin_nuevas_noticias = 0  # Reset contador

                    # Intentar cargar más resultados
                    if carga_actual < max_cargas:
                        if not self.cargar_mas_resultados():
                            print("No hay más resultados para cargar")
                            break

                        # Esperar más tiempo después de hacer clic
                        print("Esperando que carguen nuevos resultados...")
                        time.sleep(8)

                    carga_actual += 1

                print(f"Total artículos únicos encontrados: {len(news_list)}")

        except Exception as e:
            self.logger.error(f"Error extrayendo lista de noticias: {e}")

        return news_list

    def extraer_datos_articulo(self, articulo):
        """Extraer datos de un artículo específico de La Tribuna"""
        try:
            # Buscar el contenedor de información
            info_div = articulo.find('div', class_='post-main__post-info')
            if not info_div:
                return None

            # Extraer título y URL del primer enlace con h2
            titulo_link = info_div.find('a')
            if not titulo_link:
                return None

            h2 = titulo_link.find('h2')
            if not h2:
                return None

            titulo = h2.get_text().strip()
            url = titulo_link.get('href', '')

            # Construir URL completa
            if url.startswith('/'):
                url = 'https://www.latribuna.cl' + url

            # Solo devolver si tiene título y URL válidos
            if titulo and url:
                return {
                    'title': titulo,
                    'url': url
                }

        except Exception as e:
            self.logger.error(f"Error extrayendo artículo: {e}")

        return None

    def cargar_mas_resultados(self):
        """Hacer clic en el botón CARGAR MÁS con mejor detección"""
        try:
            # Intentar múltiples formas de encontrar el botón
            selectores_boton = [
                "#cargarMas",
                "buttom[id='cargarMas']",
                "button:contains('CARGAR MÁS')",
                ".cargarmas buttom",
                ".cargarmas button"
            ]

            for selector in selectores_boton:
                try:
                    if selector == "#cargarMas":
                        boton_cargar = self.driver.find_element(By.ID, "cargarMas")
                    else:
                        boton_cargar = self.driver.find_element(By.CSS_SELECTOR, selector)

                    if boton_cargar.is_displayed() and boton_cargar.is_enabled():
                        print(f"Haciendo clic en CARGAR MÁS (selector: {selector})...")
                        self.driver.execute_script("arguments[0].click();", boton_cargar)

                        # Esperar a que aparezca el spinner de carga
                        time.sleep(3)

                        # Verificar si hay spinner de carga y esperarlo
                        try:
                            spinner = self.driver.find_element(By.ID, "cargando")
                            if spinner.is_displayed():
                                print("Esperando que termine de cargar...")
                                wait = WebDriverWait(self.driver, 20)
                                wait.until_not(EC.visibility_of_element_located((By.ID, "cargando")))
                        except:
                            # Si no hay spinner, continuar
                            pass

                        return True

                except Exception:
                    continue

            print("Botón CARGAR MÁS no encontrado o no disponible")
            return False

        except Exception as e:
            print(f"Error cargando más resultados: {e}")
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

            # Extraer contenido principal
            contenido = ""

            # Buscar el contenedor principal del artículo
            main_content = soup.find('div', class_='post-main')
            if main_content:
                # Buscar párrafos dentro del contenedor principal, excluyendo scripts y elementos no deseados
                for script in main_content.find_all(['script', 'style', 'iframe']):
                    script.decompose()

                # Buscar todos los párrafos <p> que contengan texto real
                paragrafos = main_content.find_all('p')
                textos_parrafos = []

                for p in paragrafos:
                    texto = p.get_text().strip()
                    # Filtrar párrafos vacíos o muy cortos
                    if texto and len(texto) > 20:
                        textos_parrafos.append(texto)

                contenido = '\n\n'.join(textos_parrafos)

            # Si no encontramos contenido en post-main, buscar en otras áreas
            if not contenido or len(contenido) < 100:
                # Buscar h3 y párrafos siguientes que suelen ser el contenido principal
                h3_principal = soup.find('h3')
                if h3_principal:
                    contenido = h3_principal.get_text().strip() + '\n\n'

                    # Obtener párrafos hermanos después del h3
                    for sibling in h3_principal.find_next_siblings():
                        if sibling.name == 'p':
                            texto = sibling.get_text().strip()
                            if texto and len(texto) > 20:
                                contenido += texto + '\n\n'
                        elif sibling.name in ['div', 'article'] and 'chat' in sibling.get('class', []):
                            # Detenerse si llegamos a la sección de comentarios
                            break

            if contenido:
                details['content'] = contenido.strip()
                details['excerpt'] = contenido[:200] + '...' if len(contenido) > 200 else contenido

            # EXTRAER FECHA - Buscar el elemento <time> específico
            time_elem = soup.find('time')
            if time_elem:
                # Obtener el texto y limpiar el icono
                fecha_texto = time_elem.get_text().strip()
                # Remover el texto del icono si existe
                fecha_texto = re.sub(r'^\s*', '', fecha_texto).strip()

                # La fecha está en formato "08 Febrero 2025"
                fecha_normalizada = self.normalizar_fecha_latribuna(fecha_texto)
                if fecha_normalizada:
                    details['published_date'] = fecha_normalizada
                    print(f"Fecha extraída: {fecha_texto} -> {fecha_normalizada}")

            # EXTRAER IMAGEN - Buscar en el div con background-image
            img_div = soup.find('div', class_='post-image')
            if img_div and img_div.get('style'):
                # Extraer URL del style="background-image: url(...)"
                style = img_div.get('style', '')
                match = re.search(r'url\((.*?)\)', style)
                if match:
                    img_url = match.group(1).strip('"\'')
                    if img_url:
                        # Asegurar que la URL sea absoluta
                        if not img_url.startswith('http'):
                            img_url = urljoin(news_url, img_url)
                        details['image_url'] = img_url
                        print(f"Imagen extraída: {img_url}")

            # Si no encontramos imagen en post-image, buscar en otros lugares
            if not details['image_url']:
                # Buscar cualquier imagen relevante en el artículo
                img_elem = soup.find('img', src=re.compile(r'latribuna\.cl.*\.(jpg|jpeg|png|webp)', re.I))
                if img_elem and img_elem.get('src'):
                    details['image_url'] = img_elem.get('src')

            # Buscar autor
            autor_elem = soup.find('a', href=re.compile(r'/autor/'))
            if autor_elem:
                details['author'] = autor_elem.get_text().strip()

        except Exception as e:
            self.logger.error(f"Error extrayendo detalles de {news_url}: {e}")

        return details

    def normalizar_fecha_latribuna(self, fecha_texto):
        """Normalizar formato de fecha de La Tribuna"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }

        try:
            # Limpiar el texto de fecha
            fecha_limpia = fecha_texto.strip()

            # Si es formato ISO datetime
            if 'T' in fecha_limpia or (fecha_limpia.count('-') == 2 and len(fecha_limpia) >= 10):
                try:
                    return datetime.fromisoformat(fecha_limpia.replace('Z', '+00:00'))
                except:
                    pass

            # Formato típico de La Tribuna: "08 Febrero 2025"
            # Puede venir con o sin "de"
            fecha_limpia = fecha_limpia.lower()
            fecha_limpia = fecha_limpia.replace(' de ', ' ').replace(',', '').strip()

            # Dividir en partes
            partes = fecha_limpia.split()

            if len(partes) >= 3:
                try:
                    # Intentar extraer día, mes y año
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
                        fecha_resultado = datetime(año, mes_num, dia)
                        print(f"Fecha parseada correctamente: {fecha_texto} -> {fecha_resultado}")
                        return fecha_resultado
                    else:
                        print(f"No se pudo encontrar el mes '{mes_nombre}' en el diccionario")

                except ValueError as ve:
                    print(f"Error parseando partes de la fecha: {ve}")
                    pass

            # Si llegamos aquí, intentar otros formatos
            print(f"No se pudo parsear la fecha: '{fecha_texto}'")

        except Exception as e:
            self.logger.error(f"Error normalizando fecha '{fecha_texto}': {e}")

        return None
