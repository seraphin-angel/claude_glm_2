from functools import lru_cache

from langchain_community.cache import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_openai import ChatOpenAI

from app.config.settings import get_settings

set_llm_cache(InMemoryCache())


@lru_cache(maxsize=8)
def get_llm(temperature: float = 0.0, streaming: bool = False) -> ChatOpenAI:
    """LLM インスタンスをキャッシュして返す。

    同一パラメータでの呼び出しは同じインスタンスを返す。
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
        temperature=temperature,
        streaming=streaming,
    )
