import logging
import os

from openai import AsyncOpenAI

from app.core.llm.base import BaseLLMProvider
from app.core.preprocessor import EvidencePackage
from app.core.prompts import build_prompt
from app.models.incident import IncidentReport

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    async def analyse(self, package: EvidencePackage) -> IncidentReport:
        system_msg, user_msg = build_prompt(package)
        logger.info("Calling OpenAI model=%s", self.model)

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 2000)),
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format=IncidentReport,
        )

        if completion.choices[0].message.refusal:
            raise ValueError(
                f"LLM refused: {completion.choices[0].message.refusal}"
            )

        return completion.choices[0].message.parsed
