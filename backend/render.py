"""Genera el CV en DOCX, PDF y Markdown con formato ATS: una columna, sin tablas, sin imágenes,
contacto en el cuerpo (no en encabezado), secciones con nombres estándar."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
from xml.sax.saxutils import escape

TITULOS = {
    "es": {"resumen": "Resumen profesional", "habilidades": "Habilidades técnicas",
           "experiencia": "Experiencia laboral", "educacion": "Educación",
           "certificaciones": "Certificaciones", "idiomas": "Idiomas", "tecnologias": "Tecnologías",
           "actual": "Actualidad"},
    "en": {"resumen": "Professional Summary", "habilidades": "Technical Skills",
           "experiencia": "Work Experience", "educacion": "Education",
           "certificaciones": "Certifications", "idiomas": "Languages", "tecnologias": "Technologies",
           "actual": "Present"},
}


def _contacto(cv: dict) -> str:
    c = cv.get("contacto", {})
    orden = ["ubicacion", "telefono", "email", "linkedin", "github", "portafolio"]
    return " | ".join(c[k] for k in orden if c.get(k))


def _fechas(a: str, b: str, t: dict) -> str:
    b = b or t["actual"]
    return f"{a} – {b}" if a else b


# ----------------------------- DOCX -----------------------------
def docx(cv: dict, idioma: str, ruta: Path):
    t = TITULOS.get(idioma, TITULOS["es"])
    d = Document()
    for s in d.sections:
        s.top_margin = s.bottom_margin = Cm(1.8)
        s.left_margin = s.right_margin = Cm(2)
    base = d.styles["Normal"]
    base.font.name = "Calibri"
    base.font.size = Pt(10)
    base.paragraph_format.space_after = Pt(2)

    def para(texto="", bold=False, size=None, align=None, color=None, after=2, italic=False):
        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(after)
        if align:
            p.alignment = align
        r = p.add_run(texto)
        r.bold, r.italic = bold, italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        return p

    def seccion(nombre):
        p = para(nombre.upper(), bold=True, size=11.5, color="1F3864", after=3)
        p.paragraph_format.space_before = Pt(10)

    def vineta(texto):
        p = d.add_paragraph(texto, style="List Bullet")
        p.paragraph_format.space_after = Pt(1)

    para(cv["nombre"], bold=True, size=18, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
    para(cv["titular"], size=12, align=WD_ALIGN_PARAGRAPH.CENTER, after=0, color="1F3864")
    para(_contacto(cv), size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)

    if cv.get("resumen"):
        seccion(t["resumen"])
        para(cv["resumen"], after=2)

    if cv.get("habilidades"):
        seccion(t["habilidades"])
        for h in cv["habilidades"]:
            p = d.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            p.add_run(f"{h['categoria']}: ").bold = True
            p.add_run(", ".join(h["items"]))

    if cv.get("experiencia"):
        seccion(t["experiencia"])
        for e in cv["experiencia"]:
            p = para(after=0)
            p.paragraph_format.space_before = Pt(6)
            p.add_run(e["cargo"]).bold = True
            p.add_run(f" | {e['empresa']}")
            linea = _fechas(e["fecha_inicio"], e["fecha_fin"], t)
            if e.get("ubicacion"):
                linea += f" | {e['ubicacion']}"
            para(linea, size=9.5, color="555555", after=1)
            if e.get("contexto"):
                para(e["contexto"], italic=True, after=1)
            for l in e.get("logros", []):
                vineta(l)
            if e.get("tecnologias"):
                p = para(after=1)
                p.add_run(f"{t['tecnologias']}: ").bold = True
                p.add_run(", ".join(e["tecnologias"]))

    if cv.get("educacion"):
        seccion(t["educacion"])
        for ed in cv["educacion"]:
            p = para(after=1)
            p.add_run(ed["titulo"]).bold = True
            p.add_run(f" | {ed['institucion']} | {_fechas(ed['fecha_inicio'], ed['fecha_fin'], t)}")

    if cv.get("certificaciones"):
        seccion(t["certificaciones"])
        for c in cv["certificaciones"]:
            vineta(" | ".join(x for x in (c["nombre"], c["entidad"], c["fecha"]) if x))

    if cv.get("idiomas"):
        seccion(t["idiomas"])
        for i in cv["idiomas"]:
            vineta(f"{i['idioma']}: {i['nivel']}")

    d.core_properties.author = cv["nombre"]
    d.core_properties.title = f"CV {cv['nombre']} - {cv['titular']}"
    d.save(ruta)


# ----------------------------- PDF -----------------------------
def pdf(cv: dict, idioma: str, ruta: Path):
    t = TITULOS.get(idioma, TITULOS["es"])
    azul = HexColor("#1F3864")
    st = {
        "nombre": ParagraphStyle("n", fontName="Helvetica-Bold", fontSize=17, alignment=TA_CENTER, leading=21),
        "titular": ParagraphStyle("t", fontName="Helvetica", fontSize=11.5, alignment=TA_CENTER,
                                  textColor=azul, leading=15),
        "contacto": ParagraphStyle("c", fontName="Helvetica", fontSize=9, alignment=TA_CENTER, leading=12,
                                   spaceAfter=6),
        "seccion": ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=11, textColor=azul,
                                  spaceBefore=10, spaceAfter=4),
        "normal": ParagraphStyle("p", fontName="Helvetica", fontSize=9.5, leading=12.2, spaceAfter=1.5),
        "cargo": ParagraphStyle("g", fontName="Helvetica", fontSize=10, leading=12.5, spaceBefore=5),
        "meta": ParagraphStyle("m", fontName="Helvetica", fontSize=9, textColor=HexColor("#555555"), leading=12),
        "ctx": ParagraphStyle("x", fontName="Helvetica-Oblique", fontSize=9.6, leading=12.5),
    }
    E = lambda s: escape(s or "")  # noqa: E731
    flow = [Paragraph(E(cv["nombre"]), st["nombre"]), Paragraph(E(cv["titular"]), st["titular"]),
            Paragraph(E(_contacto(cv)), st["contacto"])]

    def seccion(n):
        flow.append(Paragraph(E(n.upper()), st["seccion"]))

    def lista(items):
        flow.append(ListFlowable(
            [ListItem(Paragraph(E(i), st["normal"]), leftIndent=12) for i in items],
            bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8))

    if cv.get("resumen"):
        seccion(t["resumen"])
        flow.append(Paragraph(E(cv["resumen"]), st["normal"]))
    if cv.get("habilidades"):
        seccion(t["habilidades"])
        for h in cv["habilidades"]:
            flow.append(Paragraph(f"<b>{E(h['categoria'])}:</b> {E(', '.join(h['items']))}", st["normal"]))
    if cv.get("experiencia"):
        seccion(t["experiencia"])
        for e in cv["experiencia"]:
            flow.append(Paragraph(f"<b>{E(e['cargo'])}</b> | {E(e['empresa'])}", st["cargo"]))
            meta = _fechas(e["fecha_inicio"], e["fecha_fin"], t) + (f" | {e['ubicacion']}" if e.get("ubicacion") else "")
            flow.append(Paragraph(E(meta), st["meta"]))
            if e.get("contexto"):
                flow.append(Paragraph(E(e["contexto"]), st["ctx"]))
            if e.get("logros"):
                lista(e["logros"])
            if e.get("tecnologias"):
                flow.append(Paragraph(f"<b>{E(t['tecnologias'])}:</b> {E(', '.join(e['tecnologias']))}", st["normal"]))
    if cv.get("educacion"):
        seccion(t["educacion"])
        for ed in cv["educacion"]:
            flow.append(Paragraph(f"<b>{E(ed['titulo'])}</b> | {E(ed['institucion'])} | "
                                  f"{E(_fechas(ed['fecha_inicio'], ed['fecha_fin'], t))}", st["normal"]))
    if cv.get("certificaciones"):
        seccion(t["certificaciones"])
        lista([" | ".join(x for x in (c["nombre"], c["entidad"], c["fecha"]) if x) for c in cv["certificaciones"]])
    if cv.get("idiomas"):
        seccion(t["idiomas"])
        lista([f"{i['idioma']}: {i['nivel']}" for i in cv["idiomas"]])

    doc = SimpleDocTemplate(str(ruta), pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title=f"CV {cv['nombre']}", author=cv["nombre"])
    doc.build(flow)


def contar_paginas(ruta: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(str(ruta)).pages)


# ----------------------------- Markdown -----------------------------
def markdown(cv: dict, idioma: str) -> str:
    t = TITULOS.get(idioma, TITULOS["es"])
    md = [f"# {cv['nombre']}", f"**{cv['titular']}**", "", _contacto(cv), ""]
    if cv.get("resumen"):
        md += [f"## {t['resumen']}", cv["resumen"], ""]
    if cv.get("habilidades"):
        md += [f"## {t['habilidades']}"] + [f"- **{h['categoria']}:** {', '.join(h['items'])}" for h in cv["habilidades"]] + [""]
    if cv.get("experiencia"):
        md.append(f"## {t['experiencia']}")
        for e in cv["experiencia"]:
            md += [f"### {e['cargo']} | {e['empresa']}", f"*{_fechas(e['fecha_inicio'], e['fecha_fin'], t)}*"
                   + (f" · {e['ubicacion']}" if e.get("ubicacion") else ""), ""]
            if e.get("contexto"):
                md += [e["contexto"], ""]
            md += [f"- {l}" for l in e.get("logros", [])]
            if e.get("tecnologias"):
                md += ["", f"**{t['tecnologias']}:** {', '.join(e['tecnologias'])}"]
            md.append("")
    if cv.get("educacion"):
        md += [f"## {t['educacion']}"] + [f"- **{ed['titulo']}** | {ed['institucion']} | "
                                          f"{_fechas(ed['fecha_inicio'], ed['fecha_fin'], t)}" for ed in cv["educacion"]] + [""]
    if cv.get("certificaciones"):
        md += [f"## {t['certificaciones']}"] + [f"- {c['nombre']} | {c['entidad']} {c['fecha']}".strip() for c in cv["certificaciones"]] + [""]
    if cv.get("idiomas"):
        md += [f"## {t['idiomas']}"] + [f"- {i['idioma']}: {i['nivel']}" for i in cv["idiomas"]]
    return "\n".join(md)
