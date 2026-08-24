"""Every setting in one place. Only the API key comes from .env."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

PDF_DIR = os.getenv("PDF_DIR", os.path.join(BASE_DIR, "pdfs"))
CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(BASE_DIR, "chroma_db"))
EVAL_SET = os.path.join(BASE_DIR, "data", "eval_set.json")

EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/nv-embed-v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-ai/deepseek-v3.2")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
TOP_K = 4


def require_key():
  """Fail with a readable message instead of a driver-level error later on."""
  if not NVIDIA_API_KEY:
    raise SystemExit("NVIDIA_API_KEY is not set. Copy .env.example to .env and add it.")
