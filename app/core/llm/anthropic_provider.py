import json
import logging
import os

import anthropic

from app.core.llm.base import BaseLLMProvider
from app.core.preprocessor import EvidencePackage
from app.core.prompts import build_prompt
from app.models.incident import IncidentReport

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")

    async def analyse(self, package: EvidencePackage) -> IncidentReport:
        system_msg, user_msg = build_prompt(package)
        logger.info("Calling Anthropic model=%s", self.model)

        response = await self.client.beta.messages.create(
            model=self.model,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 2000)),
            system=system_msg,
            messages=[{"role": "user", "content": user_msg}],
            betas=["structured-outputs-2025-11-13"],
            output_format={
                "type": "json_schema",
                "schema": IncidentReport.model_json_schema(),
            },
        )
        raw_json = json.loads(response.content[0].text)
        return IncidentReport.model_validate(raw_json)
