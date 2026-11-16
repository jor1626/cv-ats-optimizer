"""Llama a Claude Code en modo headless (claude -p) usando tu sesión de claude.ai."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import config


class ClaudeError(RuntimeError):
    pass


def _exe() -> str:
    found = shutil.which("claude")
    if not found:
        raise ClaudeError("No encuentro 'claude'. Instálalo con: npm install -g @anthropic-ai/claude-code")
    # En Windows, npm deja un claude.cmd; llamamos directo al .exe para no pelear con las comillas de cmd.
    exe = Path(found).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    return str(exe) if exe.exists() else found


def run(prompt: str, system_prompt: str | None = None, schema: dict | None = None,
        tools: list[str] | None = None, model: str | None = None) -> dict | str:
    """Ejecuta una consulta. Devuelve dict si se pasó schema, si no, texto."""
    config.WORKDIR.mkdir(exist_ok=True)
    cmd = [_exe(), "-p", "--output-format", "json",
           "--model", model or config.CLAUDE_MODEL,
           "--fallback-model", config.CLAUDE_FALLBACK_MODEL]
    if tools:
        cmd += ["--tools", ",".join(tools), "--allowedTools", ",".join(tools)]
    else:
        cmd += ["--tools", ""]
    if system_prompt:
        f = config.WORKDIR / "system_prompt.md"
        f.write_text(system_prompt, encoding="utf-8")
        cmd += ["--system-prompt-file", str(f)]
    if schema:
        cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]

    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
            cwd=config.WORKDIR, timeout=config.CLAUDE_TIMEOUT_S,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeError("Claude tardó demasiado en responder.") from e

    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeError(f"Respuesta inválida de Claude Code: {(proc.stderr or proc.stdout)[-800:]}") from e
    if out.get("is_error"):
        raise ClaudeError(f"Claude Code devolvió un error: {out.get('result') or out.get('subtype')}")

    if not schema:
        return out.get("result", "")
    if isinstance(out.get("structured_output"), dict):
        return out["structured_output"]
    # Respaldo: extraer el JSON del texto.
    text = out.get("result", "")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ClaudeError("Claude no devolvió el JSON esperado.")
    return json.loads(m.group(0))
