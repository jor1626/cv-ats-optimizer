# CV ATS Optimizer

Adapta tu CV a cada vacante para pasar los filtros ATS (Workday, Taleo, SuccessFactors, Greenhouse,
Computrabajo, elempleo…) **sin inventar experiencia**, y redacta el correo de postulación.
Funciona con **Claude** (tu cuenta de claude.ai vía Claude Code, sin API key) o con un **modelo local gratuito en
LM Studio u Ollama**, en tu PC o en otra máquina de la red. Corre en http://127.0.0.1:8010

## Uso

1. Doble clic en **`iniciar.bat`** (la primera vez instala dependencias).
   En **⚙️ Motor de IA** elige Claude, LM Studio u Ollama (ver abajo).
2. **Sube tu CV base** (PDF, DOCX, MD o TXT). Queda guardado para las siguientes vacantes.
3. Pega el **link** y/o el **texto de la vacante**. Si el link no carga (LinkedIn a veces bloquea),
   pega el texto: es lo más confiable.
4. Elige qué generar:
   - ☑ **Generar CV optimizado**: PDF + Word + Markdown, análisis ATS, carta y preguntas probables (1-3 min).
   - ☑ **Redactar correo de postulación**: asunto y mensaje para copiar, o abrir directo en Gmail / Outlook (~15 s si va solo).

## Dónde quedan los archivos

```
salidas/
  <empresa>/
    <vacante>/
      cv-jordan-orozco-2026-11-13.pdf   ← el que adjuntas
      cv-jordan-orozco-2026-11-13.docx
      cv-jordan-orozco-2026-11-13.md
      correo.txt
      carta_presentacion.txt
      vacante.txt
      resultado.json
```

El botón **📂 Abrir carpeta** la abre en el Explorador para arrastrar el PDF al correo
(los enlaces de Gmail/Outlook no pueden adjuntar archivos automáticamente).

## Cómo evita inventar

- La IA solo puede reformular, reordenar y usar la terminología exacta de la vacante para
  cosas que **sí** están en tu CV. Lo que te falta queda en la pestaña **Brechas**.
- La app verifica por su cuenta qué palabras clave aparecen antes y después. Las que aparecen
  en la versión nueva pero no estaban escritas en tu CV original salen en **amarillo**:
  revísalas antes de enviar.

## Formato ATS del CV generado

Una sola columna, sin tablas, imágenes ni íconos, contacto en el cuerpo (no en el encabezado),
secciones con nombres estándar, fechas MM/AAAA, texto seleccionable, máximo 2 páginas
(si se pasa, la app pide a la IA un recorte automático).

## Motor de IA

Se elige en la app (**⚙️ Motor de IA**) y se guarda en `datos/ajustes.json`.

### Claude (recomendado: mejor redacción)

Requiere [Claude Code](https://docs.claude.com/en/docs/claude-code) instalado e iniciado con tu cuenta
(`npm install -g @anthropic-ai/claude-code` y luego `claude`).

### LM Studio (gratis, sin internet)

1. Instala [LM Studio](https://lmstudio.ai) y descarga un modelo de instrucciones de 7B o más
   (p. ej. Qwen 2.5/3, Llama 3.1, Gemma 3). Los más pequeños suelen omitir campos o inventar.
2. Al cargarlo, sube **Context Length a 16384 o más**: el CV + la vacante + la respuesta no caben en 4096.
3. Pestaña **Developer → Start Server**.
4. En la app elige **LM Studio**, pon la URL y pulsa **Conectar**:
   - Mismo PC: `http://localhost:1234/v1`
   - Otra máquina de la red: `192.168.x.x:1234` (en esa máquina activa **Serve on Local Network** y
     permite el puerto en el firewall).

Sirve también con cualquier servidor compatible con la API de OpenAI (Jan, llama.cpp server, LocalAI…).

### Ollama (gratis, sin internet)

1. Instala [Ollama](https://ollama.com) y descarga un modelo de 7B o más:
   `ollama pull qwen2.5:7b` (o `llama3.1:8b`, `gemma3:12b`…).
2. En la app elige **Ollama**, pon la URL y pulsa **Conectar**:
   - Mismo PC: `http://localhost:11434`
   - Otra máquina de la red: su IP, p. ej. `192.168.1.20` (en esa máquina define la variable de entorno
     `OLLAMA_HOST=0.0.0.0`, reinicia Ollama y permite el puerto 11434 en el firewall).

La app usa la API nativa de Ollama para fijar el contexto en 16384 tokens (`OLLAMA_NUM_CTX` en
`config.py`); con el valor por defecto de Ollama el CV se recortaría sin avisar.

### Modelos locales: qué esperar

Diferencias frente a Claude: los modelos locales no abren links (pega el texto de la vacante) y la
calidad depende del modelo; revisa siempre las palabras en amarillo.

## Ajustes (`backend/config.py`)

- `CLAUDE_MODEL`: `opus` (mejor redacción) o `sonnet` (más rápido, gasta menos cupo).
- `LLM_TIMEOUT_S`: tiempo máximo de espera para modelos locales (por defecto 15 min).
- `OLLAMA_NUM_CTX`: contexto de Ollama; súbelo a 32768 si la respuesta sale cortada (usa más memoria).
- `INTERVIEW_COPILOT_PERFIL`: carpeta a la que el botón **→ Enviar a Interview Copilot** copia
  el CV optimizado, la vacante, las brechas y las preguntas probables.
