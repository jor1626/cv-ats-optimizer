"""Lee el CV (PDF, DOCX, MD, TXT) y la vacante (texto o URL)."""
import io
import json
import re

import requests
from bs4 import BeautifulSoup

import claude_cli


def _limpiar(texto: str) -> str:
    texto = re.sub(r"[ \t ]+", " ", texto)
    texto = re.sub(r"\n\s*\n\s*\n+", "\n\n", texto)
    return texto.strip()


def leer_cv(nombre: str, contenido: bytes) -> str:
    ext = nombre.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        from pypdf import PdfReader
        texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)
    elif ext == "docx":
        from docx import Document
        doc = Document(io.BytesIO(contenido))
        partes = [p.text for p in doc.paragraphs]
        for t in doc.tables:  # muchos CV ponen datos en tablas
            for fila in t.rows:
                partes.append(" | ".join(c.text for c in fila.cells))
        texto = "\n".join(partes)
    elif ext in {"md", "txt", "html", "htm"}:
        texto = contenido.decode("utf-8", errors="ignore")
        if "<" in texto and ">" in texto:  # markdown con HTML incrustado
            texto = BeautifulSoup(texto, "html.parser").get_text("\n")
    else:
        raise ValueError(f"Formato no soportado: .{ext} (usa PDF, DOCX, MD o TXT)")
    texto = _limpiar(texto)
    if len(texto) < 200:
        raise ValueError("No pude extraer texto del CV. Si es un PDF escaneado (imagen), súbelo en DOCX o TXT.")
    return texto


def _jobposting_ld(soup: BeautifulSoup) -> str | None:
    """Muchos portales (LinkedIn, Computrabajo, elempleo, Indeed) incluyen JSON-LD JobPosting."""
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "JobPosting":
                org = it.get("hiringOrganization") or {}
                desc = BeautifulSoup(it.get("description", ""), "html.parser").get_text("\n")
                return _limpiar(f"Cargo: {it.get('title', '')}\n"
                                f"Empresa: {org.get('name', '') if isinstance(org, dict) else org}\n\n{desc}")
    return None


def leer_url(url: str) -> str:
    texto = ""
    try:
        r = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        })
        if r.ok:
            soup = BeautifulSoup(r.text, "html.parser")
            texto = _jobposting_ld(soup) or ""
            if len(texto) < 300:
                for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg"]):
                    tag.decompose()
                texto = _limpiar((soup.find("main") or soup.body or soup).get_text("\n"))
    except requests.RequestException:
        pass

    if len(texto) < 300:
        # Respaldo: que Claude abra la página con su herramienta WebFetch.
        texto = claude_cli.run(
            f"Abre esta URL y devuelve SOLO el texto completo de la oferta de empleo "
            f"(cargo, empresa, descripción, requisitos, funciones, beneficios), sin comentarios: {url}",
            tools=["WebFetch"], model="sonnet",
        )
    if len(texto) < 200:
        raise ValueError("No pude leer la vacante desde el link. Copia y pega el texto de la oferta.")
    return texto[:20000]
