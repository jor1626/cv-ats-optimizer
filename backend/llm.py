"""Motor de IA: Claude Code (tu cuenta de claude.ai), LM Studio (o cualquier servidor compatible con
OpenAI) u Ollama, en tu PC o en otra IP de la red. Se elige desde la app y se guarda en
datos/ajustes.json."""
import json
import re
import shutil
from urllib.parse import urlparse

import requests

import claude_cli
import config


class LLMError(RuntimeError):
    pass


PROVEEDORES = ("claude", "lmstudio", "ollama")
AJUSTES = config.DATOS_DIR / "ajustes.json"
DEFAULT = {
    "proveedor": "claude",
    "lmstudio_url": config.LMSTUDIO_URL,
    "lmstudio_modelo": "",                 # vacío = el primer modelo disponible
    "lmstudio_api_key": "",                # solo si activaste autenticación en el servidor
    "ollama_url": config.OLLAMA_URL,
    "ollama_modelo": "",
}
NOMBRES = {"lmstudio": "LM Studio", "ollama": "Ollama"}


# ---------------- Ajustes ----------------
def cargar() -> dict:
    try:
        return {**DEFAULT, **json.loads(AJUSTES.read_text(encoding="utf-8"))}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT)


def guardar(nuevos: dict) -> dict:
    a = cargar()
    a.update({k: v for k, v in nuevos.items() if k in DEFAULT and isinstance(v, str)})
    if a["proveedor"] not in PROVEEDORES:
        raise LLMError("Proveedor no válido.")
    for p in ("lmstudio", "ollama"):
        a[f"{p}_url"] = normalizar_url(a[f"{p}_url"], p)
    AJUSTES.parent.mkdir(exist_ok=True)
    AJUSTES.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    return a


def estado() -> dict:
    """Ajustes para la interfaz (sin la API key) + si Claude Code está instalado."""
    a = cargar()
    return {**{k: v for k, v in a.items() if k != "lmstudio_api_key"},
            "tiene_api_key": bool(a["lmstudio_api_key"]),
            "claude_instalado": bool(shutil.which("claude")),
            "motor": nombre(a)}


def nombre(a: dict | None = None) -> str:
    a = a or cargar()
    p = a["proveedor"]
    if p == "claude":
        return "Claude"
    return f"{NOMBRES[p]} · {a[f'{p}_modelo'] or 'modelo por defecto'}"


def normalizar_url(url: str, proveedor: str = "lmstudio") -> str:
    """LM Studio: '192.168.1.20:1234' -> 'http://192.168.1.20:1234/v1'.
    Ollama: '192.168.1.20' -> 'http://192.168.1.20:11434' (usa la API nativa, sin /v1)."""
    defecto = config.OLLAMA_URL if proveedor == "ollama" else config.LMSTUDIO_URL
    url = (url or "").strip().rstrip("/") or defecto
    if "://" not in url:
        url = "http://" + url
    u = urlparse(url)
    if proveedor == "ollama":
        return f"{u.scheme}://{u.netloc if u.port else u.netloc + ':11434'}"
    if u.path in ("", "/"):
        url += "/v1"
    return url


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _es_local(url: str) -> bool:
    return urlparse(url).hostname in ("localhost", "127.0.0.1", "::1")


def _sin_conexion(url: str, proveedor: str) -> LLMError:
    if proveedor == "ollama":
        msg = f"No pude conectar con Ollama en {url}. Abre la app de Ollama o ejecuta 'ollama serve'."
        if not _es_local(url):
            msg += (" Como está en otra máquina, allí define la variable de entorno OLLAMA_HOST=0.0.0.0, "
                    "reinicia Ollama y permite el puerto 11434 en el firewall.")
        return LLMError(msg)
    msg = (f"No pude conectar con el servidor en {url}. En LM Studio abre la pestaña Developer y "
           "enciende el servidor (Start Server).")
    if not _es_local(url):
        msg += (" Como está en otra máquina, activa también 'Serve on Local Network' y revisa que el "
                "firewall de Windows permita el puerto.")
    return LLMError(msg)


def modelos(proveedor: str, url: str | None = None, api_key: str | None = None) -> list[str]:
    """Lista los modelos de chat disponibles (sirve también para probar la conexión)."""
    if proveedor not in NOMBRES:
        raise LLMError("Proveedor no válido.")
    a = cargar()
    url = normalizar_url(url or a[f"{proveedor}_url"], proveedor)
    api_key = (a["lmstudio_api_key"] if api_key is None else api_key) if proveedor == "lmstudio" else ""
    ruta = "/api/tags" if proveedor == "ollama" else "/models"
    try:
        r = requests.get(url + ruta, headers=_headers(api_key), timeout=8)
    except requests.RequestException as e:
        raise _sin_conexion(url, proveedor) from e
    if r.status_code in (401, 403):
        raise LLMError("El servidor pide autenticación: revisa la API key.")
    if not r.ok:
        raise LLMError(f"El servidor respondió {r.status_code}. ¿La URL es correcta?")
    if proveedor == "ollama":
        ids = [m.get("name", "") for m in r.json().get("models", [])]
    else:
        ids = [m.get("id", "") for m in r.json().get("data", [])]
    return [i for i in ids if i and "embed" not in i.lower()]


# ---------------- Consultas ----------------
def run(prompt: str, system_prompt: str | None = None, schema: dict | None = None,
        rapido: bool = False) -> dict | str:
    """Ejecuta una consulta con el motor elegido. Devuelve dict si se pasó schema, si no, texto.
    rapido=True usa el modelo de respaldo de Claude (más rápido) para tareas simples."""
    a = cargar()
    p = a["proveedor"]
    if p == "claude":
        try:
            return claude_cli.run(prompt, system_prompt=system_prompt, schema=schema,
                                  model=config.CLAUDE_FALLBACK_MODEL if rapido else None)
        except claude_cli.ClaudeError as e:
            raise LLMError(str(e)) from e

    url = normalizar_url(a[f"{p}_url"], p)
    modelo = a[f"{p}_modelo"]
    if not modelo:
        disponibles = modelos(p, url)
        if not disponibles:
            raise LLMError(f"{NOMBRES[p]} no tiene ningún modelo descargado."
                           + (" Descarga uno con: ollama pull qwen2.5:7b" if p == "ollama" else ""))
        modelo = disponibles[0]

    if p == "ollama":
        texto, cortado = _ollama(url, modelo, prompt, system_prompt, schema)
    else:
        texto, cortado = _openai(url, modelo, a["lmstudio_api_key"], prompt, system_prompt, schema)

    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()  # modelos que "piensan" en voz alta
    if cortado:
        consejo = (f"sube OLLAMA_NUM_CTX en backend/config.py (ahora {config.OLLAMA_NUM_CTX})" if p == "ollama"
                   else "en LM Studio sube el 'Context Length' del modelo (recomendado 16384 o más) y vuelve a cargarlo")
        raise LLMError(f"El modelo se quedó sin espacio y la respuesta quedó cortada: {consejo}.")
    return _parsear(texto) if schema else texto


def _post(url: str, body: dict, headers: dict, proveedor: str) -> requests.Response:
    try:
        return requests.post(url, json=body, headers=headers, timeout=(10, config.LLM_TIMEOUT_S))  # (conectar, generar)
    except requests.ConnectTimeout as e:
        raise _sin_conexion(url.rsplit("/", 2)[0], proveedor) from e
    except requests.Timeout as e:
        raise LLMError(f"El modelo tardó más de {config.LLM_TIMEOUT_S // 60} minutos. Prueba un modelo "
                       "más pequeño o con aceleración por GPU.") from e
    except requests.RequestException as e:
        raise _sin_conexion(url.rsplit("/", 2)[0], proveedor) from e


def _mensajes(prompt: str, system_prompt: str | None) -> list[dict]:
    return ([{"role": "system", "content": system_prompt}] if system_prompt else []) + \
           [{"role": "user", "content": prompt}]


def _esquema_en_prompt(system_prompt: str | None, schema: dict) -> str:
    return ((system_prompt or "") + "\n\nResponde SOLO con un objeto JSON válido (sin texto ni ``` alrededor) "
            f"que cumpla este JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}")


def _openai(url, modelo, api_key, prompt, system_prompt, schema) -> tuple[str, bool]:
    """LM Studio y cualquier servidor compatible con la API de OpenAI."""
    def pedir(con_formato: bool) -> requests.Response:
        sistema = _esquema_en_prompt(system_prompt, schema) if schema and not con_formato else system_prompt
        body = {"model": modelo, "messages": _mensajes(prompt, sistema), "temperature": 0.3, "stream": False}
        if schema and con_formato:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "respuesta", "strict": True, "schema": schema}}
        return _post(f"{url}/chat/completions", body, _headers(api_key), "lmstudio")

    r = pedir(con_formato=bool(schema))
    if schema and r.status_code == 400 and "response_format" in r.text:  # el servidor no soporta el formato
        r = pedir(con_formato=False)
    if not r.ok:
        raise LLMError(f"El servidor respondió {r.status_code}: {r.text[:400]}")
    choice = r.json()["choices"][0]
    return choice["message"].get("content") or "", choice.get("finish_reason") == "length"


def _ollama(url, modelo, prompt, system_prompt, schema) -> tuple[str, bool]:
    """API nativa de Ollama: permite fijar el contexto (num_ctx). Por la API compatible con OpenAI
    Ollama usa su contexto por defecto y recorta el inicio del prompt (el CV) sin avisar."""
    body = {"model": modelo, "messages": _mensajes(prompt, system_prompt), "stream": False,
            "options": {"num_ctx": config.OLLAMA_NUM_CTX, "temperature": 0.3}}
    if schema:
        body["format"] = schema
        # Ollama limita la salida al esquema, pero el modelo entiende mejor los campos si también los ve.
        body["messages"] = _mensajes(prompt, _esquema_en_prompt(system_prompt, schema))
    r = _post(f"{url}/api/chat", body, {}, "ollama")
    if r.status_code == 404 and "not found" in r.text:
        raise LLMError(f"Ollama no tiene el modelo '{modelo}'. Descárgalo con: ollama pull {modelo}")
    if not r.ok:
        raise LLMError(f"Ollama respondió {r.status_code}: {r.text[:400]}")
    d = r.json()
    return (d.get("message") or {}).get("content") or "", d.get("done_reason") == "length"


def _parsear(texto: str) -> dict:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError("El modelo no devolvió un JSON válido. Prueba con un modelo más grande "
                   "(se recomiendan 7B o más, p. ej. Qwen, Llama 3.1 o Gemma).")
