"""
DEPRECATED:
This module belongs to an older legal analysis flow and should not be used
as the main path for the current Legal Analyst architecture.
"""



from typing import Dict
from openai import OpenAI

from app.core.config import settings


class ClauseClassifier:

    def __init__(self):

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def classify(self, clause_text: str) -> Dict:

        prompt = f"""
You are a legal contract analysis system.

Classify the following clause into ONE category:

termination
payment
liability
confidentiality
jurisdiction
intellectual_property
other

Return ONLY JSON.

Clause:
{clause_text}
"""

        response = self.client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        text = response.output[0].content[0].text

        return {
            "classification": text.strip()
        }