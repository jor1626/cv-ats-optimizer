# CV ATS Optimizer

Adapta tu CV a cada vacante para pasar los filtros ATS (Workday, Taleo, SuccessFactors, Greenhouse,
Computrabajo, elempleo…) **sin inventar experiencia**, y redacta el correo de postulación.
Usa Claude Code con tu cuenta de claude.ai (sin API key). Corre en http://127.0.0.1:8010

## Uso

1. Doble clic en **`iniciar.bat`** (la primera vez instala dependencias).
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

- Claude solo puede reformular, reordenar y usar la terminología exacta de la vacante para
  cosas que **sí** están en tu CV. Lo que te falta queda en la pestaña **Brechas**.
- La app verifica por su cuenta qué palabras clave aparecen antes y después. Las que aparecen
  en la versión nueva pero no estaban escritas en tu CV original salen en **amarillo**:
  revísalas antes de enviar.

## Formato ATS del CV generado

Una sola columna, sin tablas, imágenes ni íconos, contacto en el cuerpo (no en el encabezado),
secciones con nombres estándar, fechas MM/AAAA, texto seleccionable, máximo 2 páginas
(si se pasa, la app pide a Claude un recorte automático).

## Ajustes (`backend/config.py`)

- `CLAUDE_MODEL`: `opus` (mejor redacción) o `sonnet` (más rápido, gasta menos cupo).
- `INTERVIEW_COPILOT_PERFIL`: carpeta a la que el botón **→ Enviar a Interview Copilot** copia
  el CV optimizado, la vacante, las brechas y las preguntas probables.
