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

# LM Studio / servidor compatible con OpenAI. La URL, el modelo y el motor activo se eligen
# desde la app (⚙️ Motor de IA) y se guardan en datos/ajustes.json; esto es solo el valor inicial.
LMSTUDIO_URL = "http://localhost:1234/v1"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_NUM_CTX = 16384              # contexto de Ollama: CV + vacante + respuesta (sube a 32768 si se corta)
LLM_TIMEOUT_S = 900                 # los modelos locales en CPU pueden tardar varios minutos

# Para el botón "Enviar a Interview Copilot" (deja None si no lo usas)
INTERVIEW_COPILOT_PERFIL = Path(r"d:\Proyectos\interview-copilot\perfil")
