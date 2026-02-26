from openai import OpenAI
from app.core.config import settings

if not settings.OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY no está cargada. Revisa tu .env.")

client = OpenAI(api_key=settings.OPENAI_API_KEY)