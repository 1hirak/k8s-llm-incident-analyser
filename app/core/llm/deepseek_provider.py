import json
import logging
import os

import httpx

from app.core.llm.base import BaseLLMProvider
from app.core.preprocessor import EvidencePackage
from app.core.prompts import build_prompt
from app.models.incident import IncidentReport

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = os.environ["DEEPSEEK_API_KEY"]
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    async def analyse(self, package: EvidencePackage) -> IncidentReport:
        system_msg, user_msg = build_prompt(package)
        logger.info("Calling DeepSeek model=%s", self.model)

        schema = IncidentReport.model_json_schema()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 2000)),
                    "response_format": {"type": "json_object", "schema": schema},
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            raw_json = json.loads(data["choices"][0]["message"]["content"])
            return IncidentReport.model_validate(raw_json)
