"""CV ATS Optimizer - http://127.0.0.1:8010"""
import json
import os
import re
import threading
import unicodedata
import webbrowser
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

import ats
import config
import esquema
import lector
import llm
import render

app = FastAPI()
for d in (config.DATOS_DIR, config.SALIDAS_DIR):
    d.mkdir(exist_ok=True)
CV_BASE_TXT = config.DATOS_DIR / "cv_base.txt"
CV_BASE_META = config.DATOS_DIR / "cv_base.json"
RID_OK = re.compile(r"[\w.-]+/[\w.-]+")


def _slug(t: str, n: int = 50) -> str:
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()[:n].strip("-")


def _slug_nombre(nombre: str) -> str:
    """'Jordan Arturo Orozco Rodriguez' -> 'jordan-orozco' (primer nombre + primer apellido)."""
    p = nombre.split()
    if len(p) >= 4:
        p = [p[0], p[2]]
    elif len(p) == 3:
        p = [p[0], p[1]]
    return _slug(" ".join(p)) or "cv"


def _carpeta(rid: str) -> Path:
    if not RID_OK.fullmatch(rid):
        raise HTTPException(404, "No existe")
    return config.SALIDAS_DIR / rid


# ---------------- CV base ----------------
@app.get("/api/cv-base")
def get_cv_base():
    if not CV_BASE_TXT.exists():
        return {"existe": False}
    meta = json.loads(CV_BASE_META.read_text(encoding="utf-8"))
    return {"existe": True, **meta, "texto": CV_BASE_TXT.read_text(encoding="utf-8")}


@app.post("/api/cv-base")
async def set_cv_base(cv: UploadFile = File(...)):
    try:
        texto = lector.leer_cv(cv.filename, await cv.read())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    CV_BASE_TXT.write_text(texto, encoding="utf-8")
    meta = {"archivo": cv.filename, "caracteres": len(texto),
            "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M")}
    CV_BASE_META.write_text(json.dumps(meta), encoding="utf-8")
    return {"existe": True, **meta, "texto": texto}


# ---------------- Motor de IA ----------------
@app.get("/api/ajustes")
def get_ajustes():
    return llm.estado()


@app.post("/api/ajustes")
def set_ajustes(datos: dict = Body(...)):
    try:
        llm.guardar(datos)
    except llm.LLMError as e:
        raise HTTPException(400, str(e)) from e
    return llm.estado()


@app.post("/api/ajustes/modelos")
def listar_modelos(datos: dict = Body(...)):
    """Prueba la conexión con LM Studio u Ollama y devuelve los modelos disponibles."""
    p = datos.get("proveedor", "lmstudio")
    api_key = datos.get("api_key") or None  # vacío = usar la guardada
    try:
        return {"url": llm.normalizar_url(datos.get("url", ""), p),
                "modelos": llm.modelos(p, datos.get("url"), api_key)}
    except llm.LLMError as e:
        raise HTTPException(400, str(e)) from e


def _validar(res, schema: dict) -> None:
    """Los modelos locales pequeños a veces omiten campos: mejor un error claro que un fallo a medias."""
    faltan = [k for k in schema.get("required", []) if not isinstance(res, dict) or k not in res]
    if faltan:
        raise ValueError(f"El modelo devolvió una respuesta incompleta (falta: {', '.join(faltan)}). "
                         "Vuelve a intentarlo o usa un modelo más grande.")
    for k, sub in schema.get("properties", {}).items():
        if sub.get("type") == "object":
            _validar(res[k], sub)


# ---------------- Procesar vacante ----------------
@app.post("/api/optimizar")
def optimizar(
    cv: UploadFile | None = File(None),
    vacante_texto: str = Form(""),
    vacante_url: str = Form(""),
    notas: str = Form(""),
    generar_cv: bool = Form(True),
    generar_correo: bool = Form(True),
):
    if not (generar_cv or generar_correo):
        raise HTTPException(400, "Marca al menos una opción: generar CV o redactar correo.")
    try:
        # 1. CV
        if cv and cv.filename:
            cv_texto = lector.leer_cv(cv.filename, cv.file.read())
        elif CV_BASE_TXT.exists():
            cv_texto = CV_BASE_TXT.read_text(encoding="utf-8")
        else:
            raise HTTPException(400, "Sube tu CV primero.")

        # 2. Vacante
        vacante = vacante_texto.strip()
        if vacante_url.strip():
            vacante = f"{lector.leer_url(vacante_url.strip())}\n\n{vacante}".strip()
        if len(vacante) < 80:
            raise HTTPException(400, "Pega el texto de la vacante o un link válido.")

        # 3. IA (Claude o LM Studio)
        if generar_cv:
            tarea = "cv+correo" if generar_correo else "cv"
            system = esquema.SYSTEM_PROMPT + (esquema.REGLAS_CORREO if generar_correo else "")
            schema = esquema.schema_completo(generar_correo)
            res = llm.run(esquema.prompt_usuario(cv_texto, vacante, notas, tarea),
                          system_prompt=system, schema=schema)
            _validar(res, schema)
            analisis = res["analisis"]
        else:
            res = llm.run(esquema.prompt_usuario(cv_texto, vacante, notas, "correo"),
                          system_prompt=esquema.SYSTEM_PROMPT_CORREO, schema=esquema.SCHEMA_SOLO_CORREO)
            _validar(res, esquema.SCHEMA_SOLO_CORREO)
            analisis = {k: res[k] for k in ("cargo_vacante", "empresa", "idioma")}
    except (ValueError, llm.LLMError) as e:
        raise HTTPException(400, str(e)) from e

    idioma = analisis.get("idioma", "es")
    fecha = datetime.now().strftime("%Y-%m-%d")

    # Carpeta: salidas/<empresa>/<vacante>/
    rid = f"{_slug(analisis.get('empresa')) or 'empresa'}/{_slug(analisis.get('cargo_vacante')) or 'vacante'}"
    out = config.SALIDAS_DIR / rid
    out.mkdir(parents=True, exist_ok=True)
    (out / "vacante.txt").write_text(vacante, encoding="utf-8")

    previo = out / "resultado.json"
    resultado = json.loads(previo.read_text(encoding="utf-8")) if previo.exists() else {}
    resultado.update({"id": rid, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                      "url": vacante_url.strip(), "carpeta": str(out), "motor": llm.nombre()})
    if not generar_cv and "analisis" in resultado:
        resultado["analisis"].update(analisis)  # conserva el análisis de una corrida anterior
    else:
        resultado["analisis"] = analisis

    if generar_cv:
        cv_nuevo = res["cv"]
        base = f"cv-{_slug_nombre(cv_nuevo['nombre'])}-{fecha}"
        pdf_path = out / f"{base}.pdf"

        # Extensión: si pasa de 2 páginas, una pasada de recorte.
        render.pdf(cv_nuevo, idioma, pdf_path)
        paginas = render.contar_paginas(pdf_path)
        if paginas > 2:
            obligatorias = [k["termino"] for k in analisis["palabras_clave"] if k["importancia"] == "obligatoria"]
            try:
                recortado = llm.run(
                    esquema.prompt_recorte(json.dumps(cv_nuevo, ensure_ascii=False), paginas, obligatorias),
                    schema=esquema.SCHEMA_CV, rapido=True)
                _validar(recortado, esquema.SCHEMA_CV)
                render.pdf(recortado, idioma, pdf_path)
                cv_nuevo, paginas = recortado, render.contar_paginas(pdf_path)
            except (llm.LLMError, ValueError):
                render.pdf(cv_nuevo, idioma, pdf_path)  # nos quedamos con la versión larga

        render.docx(cv_nuevo, idioma, out / f"{base}.docx")
        (out / f"{base}.md").write_text(render.markdown(cv_nuevo, idioma), encoding="utf-8")
        (out / "carta_presentacion.txt").write_text(res.get("carta_presentacion", ""), encoding="utf-8")
        resultado.update({
            "cv": cv_nuevo,
            "carta_presentacion": res.get("carta_presentacion", ""),
            "cobertura": ats.cobertura(analisis["palabras_clave"], cv_texto, ats.cv_a_texto(cv_nuevo)),
            "paginas": paginas,
            "archivos": {k: f"/salidas/{rid}/{base}.{k}" for k in ("pdf", "docx", "md")},
            "nombre_archivo": f"{base}.pdf",
        })

    if generar_correo:
        correo = res["correo"]
        resultado["correo"] = correo
        (out / "correo.txt").write_text(
            f"Para: {correo['destinatario']}\nAsunto: {correo['asunto']}\n\n{correo['cuerpo']}", encoding="utf-8")

    resultado["generado"] = {"cv": generar_cv, "correo": generar_correo}
    previo.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


# ---------------- Historial ----------------
@app.get("/api/historial")
def historial():
    items = []
    for f in config.SALIDAS_DIR.glob("*/*/resultado.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        items.append({"id": r["id"], "fecha": r["fecha"], "cargo": r["analisis"]["cargo_vacante"],
                      "empresa": r["analisis"]["empresa"],
                      "puntaje": r["analisis"].get("puntaje_optimizado"),
                      "tiene_cv": "cv" in r, "tiene_correo": "correo" in r})
    return sorted(items, key=lambda i: i["fecha"], reverse=True)


@app.get("/api/resultado/{rid:path}")
def resultado(rid: str):
    f = _carpeta(rid) / "resultado.json"
    if not f.exists():
        raise HTTPException(404, "No existe")
    return json.loads(f.read_text(encoding="utf-8"))


@app.post("/api/abrir/{rid:path}")
def abrir_carpeta(rid: str):
    """Abre la carpeta en el Explorador para adjuntar el CV al correo."""
    carpeta = _carpeta(rid)
    if not carpeta.exists():
        raise HTTPException(404, "No existe")
    os.startfile(carpeta)  # noqa: S606 - app local
    return {"ok": True}


@app.post("/api/copilot/{rid:path}")
def enviar_a_copilot(rid: str):
    """Copia el CV optimizado y la vacante a la carpeta perfil/ de Interview Copilot."""
    dest = config.INTERVIEW_COPILOT_PERFIL
    src = _carpeta(rid)
    if not dest or not dest.exists():
        raise HTTPException(400, "No encuentro la carpeta perfil/ de Interview Copilot (ver config.py).")
    mds = sorted(src.glob("cv-*.md"))
    if not mds:
        raise HTTPException(400, "Primero genera el CV para esta vacante.")
    r = json.loads((src / "resultado.json").read_text(encoding="utf-8"))
    for viejo in dest.glob("cv.*"):  # evita que queden dos CV en el perfil
        viejo.replace(viejo.with_name(f"_respaldo_{viejo.name}"))
    (dest / "cv.md").write_text(mds[-1].read_text(encoding="utf-8"), encoding="utf-8")
    a = r["analisis"]
    (dest / "puesto.md").write_text(
        f"# {a['cargo_vacante']} - {a['empresa']}\n\n{(src / 'vacante.txt').read_text(encoding='utf-8')}\n\n"
        "## Brechas frente a la vacante (responder con honestidad)\n"
        + "\n".join(f"- {b}" for b in a.get("brechas", []))
        + "\n\n## Preguntas probables\n" + "\n".join(f"- {p}" for p in a.get("preguntas_probables", [])) + "\n",
        encoding="utf-8")
    return {"ok": True, "destino": str(dest)}


app.mount("/salidas", StaticFiles(directory=config.SALIDAS_DIR), name="salidas")
app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    url = f"http://{config.HOST}:{config.PORT}"
    print(f"\n  CV ATS Optimizer en {url}\n")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="warning")
