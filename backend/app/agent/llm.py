"""
llm.py - Which free AI model answers.

  1st choice: Groq (very fast, free key)        -> config.GROQ_MODEL
  backup    : Google Gemini (free key)          -> config.GEMINI_MODEL
If Groq is busy (free-tier limit) or down, LangChain's with_fallbacks() asks Gemini instead,
so the customer never sees an error. Only one key is needed; both is better.
"""
from fastapi import HTTPException

from app import config


def available_models() -> list:
    names = []
    if config.GROQ_API_KEY:
        names.append(f"groq:{config.GROQ_MODEL}")
    if config.GEMINI_API_KEY:
        from app.services import gemini
        names.append(f"gemini:{gemini._chosen or config.GEMINI_MODEL}")
    return names


def chat_model(tools):
    """A chat model that can call our tools, with the backup already attached."""
    models = []
    if config.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        models.append(ChatGroq(model=config.GROQ_MODEL, api_key=config.GROQ_API_KEY,
                               temperature=config.LLM_TEMPERATURE, timeout=config.LLM_TIMEOUT_SECONDS,
                               max_retries=1))
    if config.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.services import gemini
        gemini_name = gemini.chat_model_name()          # no waiting: Groq answers first anyway
        if gemini_name:
            models.append(ChatGoogleGenerativeAI(model=gemini_name, google_api_key=config.GEMINI_API_KEY,
                                                 temperature=config.LLM_TEMPERATURE,
                                                 timeout=config.LLM_TIMEOUT_SECONDS, max_retries=1))
    if not models:
        raise HTTPException(503, "The AI assistant is not set up yet (no GROQ_API_KEY or GEMINI_API_KEY in "
                                 "backend/.env). The quick calculator still works.")
    bound = [m.bind_tools(tools) for m in models]
    return bound[0].with_fallbacks(bound[1:]) if len(bound) > 1 else bound[0]
