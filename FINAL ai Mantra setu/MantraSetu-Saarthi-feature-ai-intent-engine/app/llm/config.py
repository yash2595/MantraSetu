"""LLM configuration module alias pointing to app.llm.settings."""

from app.llm.settings import LLMSettings, get_llm_settings, llm_settings

__all__ = ["LLMSettings", "get_llm_settings", "llm_settings"]