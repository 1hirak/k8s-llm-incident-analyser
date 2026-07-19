import os

from app.core.llm.base import BaseLLMProvider


def get_provider() -> BaseLLMProvider:
    provider = os.environ.get("LLM_PROVIDER", "mock").lower()
    if provider == "openai":
        from app.core.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider == "anthropic":
        from app.core.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    elif provider == "deepseek":
        from app.core.llm.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()
    else:
        from app.core.llm.mock_provider import MockProvider
        return MockProvider()
