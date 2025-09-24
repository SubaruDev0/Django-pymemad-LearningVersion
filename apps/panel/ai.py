import logging
import os

from django.utils.html import strip_tags
from openai import OpenAI

logger = logging.getLogger(__name__)


def get_post_ai(body, user_instructions=None):
    logger.info("="*50)
    logger.info("FUNCIÓN get_post_ai INICIADA")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    api_url = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
    
    logger.info(f"API URL: {api_url}")
    logger.info(f"API Key configurada: {'Sí' if api_key else 'No'}")
    logger.info(f"Longitud del contenido recibido: {len(body)} caracteres")

    client_deepseek = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("DEEPSEEK_API_URL")
    )

    # Limitar el contenido del body si es muy largo
    original_length = len(body)
    if len(body) > 3000:
        body = body[:3000] + "..."
        logger.warning(f"⚠️ Contenido truncado de {original_length} a 3000 caracteres")

    # Definición clara y concisa del rol del sistema.
    system_prompt = """
    Eres un asistente de IA especializado en la redacción de noticias para un medio escrito. Tu tarea es generar una nota para nuestro portal basada en el contexto proporcionado, de una extensión de 500 palabras. La nota debe ser informativa, escrita en un lenguaje claro y accesible. El formato debe incluir:
    - Titular: frase corta y atractiva.
    - Bajada/Subtítulo: breve párrafo que complementa el titular.
    - Cuerpo de la nota: organizado en párrafos, seguir la estructura de pirámide invertida comenzando con lo más importante.
    Utiliza Markdown para la presentación.
    - Indentifica las 5 palabras claves más relevantes sobre el tema de la nota.
    """

    # Instrucciones claras para el usuario.
    if user_instructions:
        user_prompt = f"""
        Por favor, genera una nota basada en el siguiente contexto: {body}
        
        Instrucciones adicionales del usuario: {user_instructions}
        
        Gracias por tu ayuda.
        """
        logger.info(f"Usando instrucciones personalizadas: {user_instructions[:100]}...")
    else:
        user_prompt = f"""
        Por favor, genera una nota basada en el siguiente contexto: {body}. Gracias por tu ayuda.
        """
        logger.info("Sin instrucciones adicionales del usuario")

    logger.info(f"Longitud del prompt final: {len(user_prompt)} caracteres")
    logger.info("Enviando solicitud a DeepSeek API...")
    logger.info(f"Parámetros: model=deepseek-chat, temperature=0.3, max_tokens=2000, timeout=90")

    try:
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Reducido para más consistencia
            max_tokens=2000,  # Ajustado al rango válido de DeepSeek
            timeout=90
        )

        content = response.choices[0].message.content
        logger.info(f"✅ Respuesta recibida exitosamente")
        logger.info(f"Longitud de la respuesta: {len(content)} caracteres")
        logger.info(f"Primeros 200 caracteres de la respuesta: {content[:200]}...")
        
        return content
    
    except Exception as e:
        logger.error(f"Error en get_post_ai: {str(e)}")
        # Si falla, intentar con parámetros más conservadores
        try:
            logger.info("Reintentando con parámetros más conservadores...")
            response = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt[:1500]}  # Limitar prompt
                ],
                temperature=0.1,
                max_tokens=1000,
                timeout=30
            )
            content = response.choices[0].message.content
            logger.info("Contenido AI generado en segundo intento")
            return content
        except Exception as e2:
            logger.error(f"Error en segundo intento: {str(e2)}")
            raise


def get_post_translation(title, placeholders, target_language):
    client_deepseek = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("DEEPSEEK_API_URL")
    )

    system_prompt = (
        "Eres un traductor profesional. Traduce fielmente manteniendo estructura y placeholders."
    )

    texts = [f"{key}: {value}" for key, value in placeholders.items()]
    user_prompt = (
        f"Traduce estos textos del español al {target_language}, manteniendo placeholders:\n\n"
        f"TÍTULO: {title}\n"
        + "\n".join(texts)
        + "\n\nDevuelve en formato:\n"
          "TÍTULO: [titulo traducido]\n"
          "{{TEXT_1}}: [traducción]\n{{TEXT_2}}: [traducción]\n..."
    )

    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=4000,
        timeout=90
    )

    content = response.choices[0].message.content

    lines = content.strip().split('\n')
    title_translated = lines[0].replace('TÍTULO:', '').strip()

    # Corrección adicional: eliminar "TITLE:" si se incluye por error
    if title_translated.upper().startswith("TITLE:"):
        title_translated = title_translated[6:].strip()

    placeholders_translated = {}
    for line in lines[1:]:
        if ':' in line:
            key, val = line.split(':', 1)
            placeholders_translated[key.strip()] = val.strip()

    return title_translated, placeholders_translated


def generate_meta_description(title, body, lang='es', keywords=None, category=None):
    """
    Genera meta descripción SEO optimizada usando DeepSeek.

    Args:
        title: Título del post
        body: Contenido del post (HTML)
        lang: Código de idioma ('es', 'en', 'pt')
        keywords: Lista de palabras clave opcionales
        category: Categoría del post

    Returns:
        Meta descripción de 150-160 caracteres o None si falla
    """
    client_deepseek = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
    )

    # Limpiar contenido HTML
    clean_body = strip_tags(body).strip()
    if len(clean_body) > 800:
        clean_body = clean_body[:800] + "..."

    # Prompts por idioma
    system_prompts = {
        'es': "Eres un experto en SEO. Genera meta descripciones de exactamente 150-160 caracteres que sean atractivas y contengan palabras clave relevantes.",
        'en': "You are an SEO expert. Generate meta descriptions of exactly 150-160 characters that are compelling and contain relevant keywords.",
        'pt': "Você é um especialista em SEO. Gere meta descrições de exatamente 150-160 caracteres que sejam atraentes e contenham palavras-chave relevantes."
    }

    # Contexto adicional
    context_parts = []
    if category:
        context_parts.append(f"CATEGORÍA: {category}")
    if keywords and len(keywords) > 0:
        context_parts.append(f"PALABRAS CLAVE: {', '.join(keywords[:5])}")

    additional_context = "\n".join(context_parts) if context_parts else ""

    user_prompt = (
        f"Genera una meta descripción SEO para este artículo:\n\n"
        f"TÍTULO: {title}\n"
        f"CONTENIDO: {clean_body}\n"
        f"{additional_context}\n\n"
        f"Devuelve SOLO la meta descripción en formato:\n"
        f"META: [meta descripción de 150-160 caracteres]"
    )

    try:
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompts.get(lang, system_prompts['es'])},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=200,
            timeout=30
        )

        content = response.choices[0].message.content.strip()

        # Extraer la meta descripción
        if content.startswith("META:"):
            meta_description = content.replace("META:", "").strip()
        else:
            # Si no sigue el formato, usar todo el contenido
            meta_description = content

        # Limpiar comillas si las tiene
        meta_description = meta_description.strip('"\'')

        # Validar y ajustar longitud
        if len(meta_description) > 160:
            # Cortar en el último espacio antes de 157 caracteres
            meta_description = meta_description[:157]
            last_space = meta_description.rfind(' ')
            if last_space > 140:
                meta_description = meta_description[:last_space] + "..."
            else:
                meta_description = meta_description + "..."

        logger.info(f"Meta descripción generada: {len(meta_description)} caracteres")
        return meta_description

    except Exception as e:
        logger.error(f"Error generando meta descripción: {str(e)}")
        return None


def generate_meta_descriptions_batch(posts_data):
    """
    Genera meta descripciones para múltiples posts y sus traducciones en una sola llamada.
    Más eficiente que llamar generate_meta_description múltiples veces.

    Args:
        posts_data: Lista de diccionarios con datos de posts
        [{
            'id': 1,
            'translations': {
                'es': {'title': '...', 'body': '...'},
                'en': {'title': '...', 'body': '...'},
                'pt': {'title': '...', 'body': '...'}
            },
            'keywords': ['...'],
            'category': '...'
        }]

    Returns:
        Dict con las meta descripciones generadas por post e idioma
        {post_id: {'es': 'meta...', 'en': 'meta...', 'pt': 'meta...'}}
    """
    client_deepseek = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
    )

    results = {}

    for post in posts_data:
        post_id = post['id']
        results[post_id] = {}

        # Preparar todas las metas a generar
        metas_to_generate = []

        for lang in ['es', 'en', 'pt']:
            if lang in post.get('translations', {}):
                trans = post['translations'][lang]
                if trans.get('title') and trans.get('body'):
                    clean_body = strip_tags(trans['body']).strip()
                    if len(clean_body) > 800:
                        clean_body = clean_body[:800] + "..."

                    metas_to_generate.append({
                        'lang': lang,
                        'title': trans['title'],
                        'body': clean_body
                    })

        if not metas_to_generate:
            logger.warning(f"Post {post_id} no tiene traducciones válidas para generar metas")
            continue

        # Generar prompt para todas las metas de una vez
        system_prompt = (
            "Eres un experto en SEO multilingüe. Genera meta descripciones optimizadas "
            "de exactamente 150-160 caracteres para cada idioma solicitado. "
            "Cada meta descripción debe ser atractiva, contener palabras clave relevantes "
            "y estar adaptada culturalmente a cada idioma."
        )

        user_prompt = "Genera meta descripciones SEO para estos artículos:\n\n"

        # Agregar cada idioma al prompt
        for meta_data in metas_to_generate:
            lang_name = {
                'es': 'ESPAÑOL',
                'en': 'INGLÉS',
                'pt': 'PORTUGUÉS'
            }[meta_data['lang']]

            user_prompt += (
                f"=== {lang_name} ===\n"
                f"TÍTULO: {meta_data['title']}\n"
                f"CONTENIDO: {meta_data['body']}\n\n"
            )

        # Agregar contexto común si existe
        if post.get('keywords'):
            keywords_str = ', '.join(post['keywords'][:5])
            user_prompt += f"PALABRAS CLAVE COMUNES: {keywords_str}\n"

        if post.get('category'):
            user_prompt += f"CATEGORÍA: {post['category']}\n"

        user_prompt += (
            "\nDevuelve ÚNICAMENTE las meta descripciones en este formato exacto:\n"
            "ES: [meta descripción en español]\n"
            "EN: [meta descripción en inglés]\n"
            "PT: [meta descripción en portugués]\n\n"
            "IMPORTANTE: Solo incluye los idiomas que fueron solicitados arriba."
        )

        try:
            response = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=600,
                timeout=60
            )

            content = response.choices[0].message.content.strip()

            # Parsear respuesta línea por línea
            lines = content.split('\n')

            for line in lines:
                line = line.strip()

                # Procesar línea ES
                if line.startswith('ES:') and 'es' in [m['lang'] for m in metas_to_generate]:
                    meta = line.replace('ES:', '').strip().strip('"\'')
                    if 100 <= len(meta) <= 200:  # Validación de longitud razonable
                        # Ajustar si es necesario
                        if len(meta) > 160:
                            meta = meta[:157]
                            last_space = meta.rfind(' ')
                            if last_space > 140:
                                meta = meta[:last_space] + "..."
                        results[post_id]['es'] = meta

                # Procesar línea EN
                elif line.startswith('EN:') and 'en' in [m['lang'] for m in metas_to_generate]:
                    meta = line.replace('EN:', '').strip().strip('"\'')
                    if 100 <= len(meta) <= 200:
                        if len(meta) > 160:
                            meta = meta[:157]
                            last_space = meta.rfind(' ')
                            if last_space > 140:
                                meta = meta[:last_space] + "..."
                        results[post_id]['en'] = meta

                # Procesar línea PT
                elif line.startswith('PT:') and 'pt' in [m['lang'] for m in metas_to_generate]:
                    meta = line.replace('PT:', '').strip().strip('"\'')
                    if 100 <= len(meta) <= 200:
                        if len(meta) > 160:
                            meta = meta[:157]
                            last_space = meta.rfind(' ')
                            if last_space > 140:
                                meta = meta[:last_space] + "..."
                        results[post_id]['pt'] = meta

            # Verificar que se generaron todas las metas esperadas
            generated_langs = list(results[post_id].keys())
            expected_langs = [m['lang'] for m in metas_to_generate]

            if len(generated_langs) < len(expected_langs):
                missing = set(expected_langs) - set(generated_langs)
                logger.warning(
                    f"Post {post_id}: Faltan metas para idiomas {missing}. "
                    f"Esperados: {expected_langs}, Generados: {generated_langs}"
                )
            else:
                logger.info(
                    f"Post {post_id}: Metas generadas exitosamente para {generated_langs}"
                )

        except Exception as e:
            logger.error(f"Error generando metas batch para post {post_id}: {str(e)}")
            # En caso de error, intentar generar individualmente como fallback
            logger.info(f"Intentando generar metas individualmente para post {post_id}")

            for meta_data in metas_to_generate:
                try:
                    individual_meta = generate_meta_description(
                        title=meta_data['title'],
                        body=meta_data['body'],
                        lang=meta_data['lang'],
                        keywords=post.get('keywords'),
                        category=post.get('category')
                    )

                    if individual_meta:
                        results[post_id][meta_data['lang']] = individual_meta

                except Exception as e2:
                    logger.error(
                        f"Error generando meta individual para post {post_id} "
                        f"en {meta_data['lang']}: {str(e2)}"
                    )

    return results


# Función helper adicional para procesar un solo post (útil para testing)
def generate_all_metas_for_single_post(post):
    """
    Helper conveniente para generar todas las metas de un post Django.

    Args:
        post: Instancia del modelo Post

    Returns:
        Dict con las metas generadas por idioma
    """
    # Preparar datos del post
    post_data = {
        'id': post.id,
        'translations': {},
        'keywords': [tag.name for tag in post.tags.all()],
        'category': post.category.name if post.category else None
    }

    # Obtener todas las traducciones
    for lang in ['es', 'en', 'pt']:
        if post.has_translation(lang):
            post.set_current_language(lang)
            title = post.safe_translation_getter('title')
            body = post.safe_translation_getter('body')

            if title and body:
                post_data['translations'][lang] = {
                    'title': title,
                    'body': body
                }

    # Generar metas
    results = generate_meta_descriptions_batch([post_data])

    # Retornar solo las metas de este post
    return results.get(post.id, {})
