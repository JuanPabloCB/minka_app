import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


class AIGateway:
    """
    Unified AI gateway for Minka.

    Supports multiple providers (Anthropic, OpenAI, etc.)
    and standardizes response generation.
    """

    def __init__(self):

        self.provider = os.getenv("AI_PROVIDER", "anthropic")

        if self.provider == "anthropic":

            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is missing in .env")

            self.client = Anthropic(api_key=api_key)

            # model configurable via .env
            self.model = os.getenv(
                "AI_MODEL",
                "claude-sonnet-4-6"
            )

        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def generate(self, prompt: str, temperature: float = 0) -> str:
        """
        Send prompt to AI provider and return text response.
        """

        if self.provider == "anthropic":

            try:

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=temperature,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                # Claude responses come as content blocks
                if response.content and len(response.content) > 0:
                    return response.content[0].text

                return ""

            except Exception as e:
                raise RuntimeError(f"AI request failed: {str(e)}")