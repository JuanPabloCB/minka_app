# app/core/openai_client.py
from openai import OpenAI
from app.core.config import settings

_client: OpenAI | None = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY no está cargada. Revisa tu .env.")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client