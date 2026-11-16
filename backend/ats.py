"""Verificación independiente de Claude: ¿qué palabras clave aparecen en cada versión del CV?"""
import re
import unicodedata


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # quita tildes
    return re.sub(r"\s+", " ", t)


def _aparece(variantes: list[str], texto: str) -> bool:
    for v in variantes:
        v = normalizar(v).strip()
        if not v:
            continue
        # Límites de palabra que respetan términos como "C#", "Node.js", ".NET", "CI/CD".
        if re.search(rf"(?<![\w]){re.escape(v)}(?![\w])", texto):
            return True
    return False


def cobertura(palabras_clave: list[dict], cv_original: str, cv_nuevo: str) -> dict:
    orig, nuevo = normalizar(cv_original), normalizar(cv_nuevo)
    filas, peso_total, peso_o, peso_n = [], 0.0, 0.0, 0.0
    for kw in palabras_clave:
        variantes = [kw["termino"], *kw.get("sinonimos", [])]
        en_o, en_n = _aparece(variantes, orig), _aparece(variantes, nuevo)
        peso = 2.0 if kw.get("importancia") == "obligatoria" else 1.0
        peso_total += peso
        peso_o += peso * en_o
        peso_n += peso * en_n
        estado = ("presente" if en_o and en_n else
                  "agregada" if en_n else
                  "perdida" if en_o else "faltante")
        filas.append({**kw, "en_original": en_o, "en_optimizado": en_n, "estado": estado})
    pct = lambda x: round(100 * x / peso_total) if peso_total else 0  # noqa: E731
    return {"original": pct(peso_o), "optimizado": pct(peso_n), "palabras": filas}


def cv_a_texto(cv: dict) -> str:
    """Texto plano del CV optimizado (lo que leería un ATS)."""
    c = cv.get("contacto", {})
    partes = [cv.get("nombre", ""), cv.get("titular", ""), " | ".join(v for v in c.values() if v),
              cv.get("resumen", "")]
    for h in cv.get("habilidades", []):
        partes.append(f"{h['categoria']}: {', '.join(h['items'])}")
    for e in cv.get("experiencia", []):
        partes += [f"{e['cargo']} - {e['empresa']} ({e['fecha_inicio']} - {e['fecha_fin']})",
                   e.get("contexto", ""), *e.get("logros", []), ", ".join(e.get("tecnologias", []))]
    for ed in cv.get("educacion", []):
        partes.append(f"{ed['titulo']} - {ed['institucion']}")
    for ce in cv.get("certificaciones", []):
        partes.append(f"{ce['nombre']} - {ce['entidad']}")
    for i in cv.get("idiomas", []):
        partes.append(f"{i['idioma']}: {i['nivel']}")
    return "\n".join(p for p in partes if p)
