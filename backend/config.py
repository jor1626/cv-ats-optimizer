from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "frontend"
DATOS_DIR = ROOT / "datos"          # aquí se guarda tu CV base
SALIDAS_DIR = ROOT / "salidas"      # un subdirectorio por cada vacante procesada
WORKDIR = ROOT / ".claude_workdir"  # carpeta vacía donde corre Claude Code

HOST = "127.0.0.1"
PORT = 8010

# Claude Code con tu sesión de claude.ai
CLAUDE_MODEL = "opus"               # mejor calidad de redacción; si se agota el cupo usa el de respaldo
CLAUDE_FALLBACK_MODEL = "sonnet"
CLAUDE_TIMEOUT_S = 600

# Para el botón "Enviar a Interview Copilot" (deja None si no lo usas)
INTERVIEW_COPILOT_PERFIL = Path(r"d:\Proyectos\interview-copilot\perfil")
