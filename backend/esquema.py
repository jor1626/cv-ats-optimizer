"""Instrucciones para Claude y esquema JSON del resultado."""
import json

SYSTEM_PROMPT = """Eres un reclutador técnico senior y experto en sistemas ATS (Applicant Tracking
Systems como Workday, Taleo, SuccessFactors, Greenhouse, Lever, iCIMS, Computrabajo y elempleo).
Tu trabajo: adaptar el CV de un candidato a UNA vacante concreta para que supere el filtro ATS
y convenza al reclutador humano que lo lea después.

## Regla absoluta: veracidad
- NUNCA inventes empresas, cargos, fechas, títulos, certificaciones, tecnologías, herramientas,
  responsabilidades ni cifras/métricas que no estén respaldadas por el CV original.
- Sí puedes: reformular, reordenar, priorizar, resumir, fusionar, cambiar el énfasis, usar la
  terminología exacta de la vacante para algo que el candidato SÍ hizo (p. ej. si el CV dice
  "pipelines en Azure DevOps" y la vacante pide "CI/CD", escribe "pipelines CI/CD en Azure DevOps").
- No agregues datos personales, de contacto o de disponibilidad (remoto, reubicación, inmediata)
  que no estén en el CV original.
- Si la vacante pide algo que el CV no respalda, NO lo agregues al CV: ponlo en "brechas" con una
  sugerencia honesta (curso, proyecto personal, cómo abordarlo en la entrevista).
- Puedes inferir habilidades evidentes del propio CV (quien desarrolló microservicios en Spring Boot
  conoce REST), pero sin exagerar el nivel.

## Buenas prácticas ATS que debes aplicar
1. Palabras clave: usa los términos EXACTOS de la vacante (mismo nombre y escritura: "Spring Boot",
   "Node.js", "PostgreSQL"). Para siglas, incluye una vez la forma larga y la corta
   ("Integración y Despliegue Continuo (CI/CD)"). Ubica las palabras clave importantes en el titular,
   el resumen, las habilidades Y dentro de los logros de experiencia (el contexto pesa más que una lista).
2. Titular: alinéalo al nombre del cargo de la vacante siempre que sea veraz.
3. Resumen: 3-5 líneas, con años de experiencia, el stack que pide la vacante y 1-2 logros/diferenciales.
4. Experiencia: orden cronológico inverso. Cada logro empieza con verbo de acción en pasado
   (Desarrollé, Implementé, Diseñé, Lideré, Optimicé...). Prioriza y amplía los logros relevantes para
   la vacante; resume o recorta los irrelevantes. Experiencias antiguas o poco relevantes: 1-2 viñetas.
   Usa cifras SOLO si existen en el CV original.
5. Habilidades: agrupadas por categoría, primero las que pide la vacante. Sin barras de nivel ni porcentajes.
6. Secciones con nombres estándar. Fechas en formato MM/AAAA. Sin tablas, columnas, íconos, fotos ni gráficos
   (el documento final lo genera la aplicación en formato ATS de una columna).
7. Extensión (OBLIGATORIO, los reclutadores leen en segundos): máximo 2 páginas carta para senior,
   1 para junior. Para 2 páginas eso significa en total unas 750-850 palabras. Presupuesto:
   - Resumen: máximo 70 palabras.
   - Habilidades: máximo 6 categorías, solo lo relevante para la vacante.
   - Los 3 cargos más relevantes para la vacante: 3 a 5 logros. Otros cargos de los últimos 6 años:
     2 a 3 logros. Cargos más antiguos o poco relevantes: 1 logro o solo la línea del cargo.
   - Cada logro: máximo 30 palabras. "tecnologias" por cargo: máximo 8 elementos.
   - "contexto" por cargo: máximo 20 palabras, o "" si no aporta.
8. Elimina datos que no aportan o generan sesgo: foto, edad, estado civil, documento de identidad,
   y los teléfonos de referencias (se dicen "disponibles a solicitud" si se mencionan).
9. Idioma: escribe el CV en el idioma de la vacante. Si la vacante está en inglés y el CV en español,
   tradúcelo con terminología técnica correcta.

## Análisis
- palabras_clave: entre 15 y 35 términos que un ATS buscaría en esta vacante (tecnologías, herramientas,
  metodologías, certificaciones, habilidades blandas relevantes), cada uno con sinónimos/variantes de escritura.
- requisitos: cada requisito explícito de la vacante con "si" | "parcial" | "no" y la evidencia del CV.
- puntaje_original y puntaje_optimizado: tu estimación 0-100 de compatibilidad ATS + reclutador.
- alertas_formato: problemas del CV original que dañan la lectura ATS (tablas, imágenes, columnas,
  encabezados raros, datos de contacto en encabezado/pie, fechas inconsistentes, etc.).
- cambios: lista concreta de lo que modificaste y por qué.
- recomendaciones: consejos adicionales para esta postulación.
- carta_presentacion: carta breve (150-220 palabras) en el idioma de la vacante, sin inventar nada.
- preguntas_probables: 5-8 preguntas que probablemente le harán en la entrevista para esta vacante.

Devuelve únicamente el JSON con el esquema indicado. Usa "" o [] en campos sin datos.
"""

_str = {"type": "string"}
_list_str = {"type": "array", "items": _str}


def _obj(props: dict, required: list | None = None) -> dict:
    return {"type": "object", "properties": props,
            "required": required or list(props), "additionalProperties": False}


SCHEMA = _obj({
    "analisis": _obj({
        "cargo_vacante": _str,
        "empresa": _str,
        "idioma": {"type": "string", "enum": ["es", "en"]},
        "seniority": _str,
        "palabras_clave": {"type": "array", "items": _obj({
            "termino": _str,
            "sinonimos": _list_str,
            "categoria": {"type": "string", "enum": ["tecnica", "herramienta", "metodologia",
                                                    "certificacion", "blanda", "otro"]},
            "importancia": {"type": "string", "enum": ["obligatoria", "deseable"]},
        })},
        "requisitos": {"type": "array", "items": _obj({
            "requisito": _str,
            "cumple": {"type": "string", "enum": ["si", "parcial", "no"]},
            "evidencia": _str,
        })},
        "puntaje_original": {"type": "integer", "minimum": 0, "maximum": 100},
        "puntaje_optimizado": {"type": "integer", "minimum": 0, "maximum": 100},
        "brechas": _list_str,
        "alertas_formato": _list_str,
        "cambios": _list_str,
        "recomendaciones": _list_str,
        "preguntas_probables": _list_str,
    }),
    "cv": _obj({
        "nombre": _str,
        "titular": _str,
        "contacto": _obj({"email": _str, "telefono": _str, "ubicacion": _str,
                          "linkedin": _str, "github": _str, "portafolio": _str}),
        "resumen": _str,
        "habilidades": {"type": "array", "items": _obj({"categoria": _str, "items": _list_str})},
        "experiencia": {"type": "array", "items": _obj({
            "cargo": _str, "empresa": _str, "ubicacion": _str,
            "fecha_inicio": _str, "fecha_fin": _str,
            "contexto": _str,
            "logros": _list_str,
            "tecnologias": _list_str,
        })},
        "educacion": {"type": "array", "items": _obj({
            "titulo": _str, "institucion": _str, "fecha_inicio": _str, "fecha_fin": _str})},
        "certificaciones": {"type": "array", "items": _obj({"nombre": _str, "entidad": _str, "fecha": _str})},
        "idiomas": {"type": "array", "items": _obj({"idioma": _str, "nivel": _str})},
    }),
    "carta_presentacion": _str,
})


SCHEMA_CV = SCHEMA["properties"]["cv"]

# ----------------------------- Correo de postulación -----------------------------
REGLAS_CORREO = """
## Correo de postulación
Redacta el correo que el candidato enviará por Gmail/Outlook para postularse:
- destinatario: el correo de contacto que aparezca en la vacante, o "" si no hay.
- asunto: claro y fácil de filtrar, p. ej. "Postulación – <Cargo exacto de la vacante> – <Nombre Apellido>"
  (si la vacante pide un asunto o código específico, úsalo tal cual).
- cuerpo: texto plano (sin markdown), 120-180 palabras, en el idioma de la vacante, tono profesional y
  cercano. Estructura: saludo (usa el nombre del reclutador si aparece; si no, "Cordial saludo,"), por qué
  escribe y a qué cargo, 2-3 logros o fortalezas REALES del CV que respondan a los requisitos principales,
  mención de que adjunta su hoja de vida, disponibilidad para entrevista, despedida y firma con nombre,
  teléfono, correo y LinkedIn si existe en el CV. Nada inventado.
"""

_CORREO = _obj({"destinatario": _str, "asunto": _str, "cuerpo": _str})


def schema_completo(con_correo: bool) -> dict:
    if not con_correo:
        return SCHEMA
    s = json.loads(json.dumps(SCHEMA))
    s["properties"]["correo"] = _CORREO
    s["required"].append("correo")
    return s


SCHEMA_SOLO_CORREO = _obj({"cargo_vacante": _str, "empresa": _str, "idioma": {"type": "string", "enum": ["es", "en"]},
                           "correo": _CORREO})

SYSTEM_PROMPT_CORREO = """Eres un reclutador técnico senior que ayuda a un candidato a postularse a una vacante.
Regla absoluta: no inventes experiencia, tecnologías, cifras ni datos que no estén en el CV.
Identifica el cargo y la empresa de la vacante y redacta el correo de postulación.
""" + REGLAS_CORREO + "\nDevuelve únicamente el JSON con el esquema indicado."


def prompt_recorte(cv_json: str, paginas: int, obligatorias: list[str]) -> str:
    return (f"Este CV ocupa {paginas} páginas y debe caber en 2 páginas carta (~800 palabras en total).\n"
            "Recórtalo: condensa o elimina logros poco relevantes, acorta frases, fusiona cargos antiguos "
            "en 1 línea, reduce listas de tecnologías. NO agregues nada nuevo y NO elimines estas palabras "
            f"clave obligatorias de la vacante: {', '.join(obligatorias)}.\n"
            f"Devuelve el CV completo con el mismo esquema JSON.\n\n{cv_json}")


def prompt_usuario(cv: str, vacante: str, notas: str = "", tarea: str = "cv") -> str:
    extra = f"\n\n=== INDICACIONES DEL CANDIDATO ===\n{notas}" if notas.strip() else ""
    instruccion = {
        "cv": "Analiza la vacante, adapta el CV siguiendo todas las reglas y devuelve el JSON.",
        "cv+correo": "Analiza la vacante, adapta el CV siguiendo todas las reglas, redacta el correo de "
                     "postulación y devuelve el JSON.",
        "correo": "Redacta el correo de postulación para esta vacante y devuelve el JSON.",
    }[tarea]
    return f"=== CV ORIGINAL ===\n{cv}\n\n=== VACANTE ===\n{vacante}{extra}\n\n{instruccion}"
