# orchestrator/app/core/config.py

import os
from dotenv import load_dotenv
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# Pull in any .env file
load_dotenv()

class Settings(BaseSettings):
    # — Telegram
    TELEGRAM_TOKEN: str
    WEBHOOK_SECRET: str

    # — LLM backend
    LLM_BACKEND: str = "openai"           # "openai" or "llama"
    OPENAI_API_KEY: Optional[str] = None
    LLAMA_MODEL_PATH: Optional[str] = None

    # — RabbitMQ
    RABBITMQ_URL: str

    # — n8n
    N8N_WEBHOOK_URL: str
    N8N_USER: str
    N8N_PASSWORD: str

    # — Pinecone: case-law
    CASELAW_PINECONE_API_KEY: str
    CASELAW_PINECONE_ENVIRONMENT: str
    CASELAW_PINECONE_INDEX: str

    # — Pinecone: memo
    MEMO_PINECONE_API_KEY: str
    MEMO_PINECONE_ENVIRONMENT: str
    MEMO_PINECONE_INDEX: str

    # — Pinecone: generic
    PINECONE_API_KEY: str
    PINECONE_ENV: str

    model_config = SettingsConfigDict(
        extra="ignore"  # drop any undeclared vars
    )

    @model_validator(mode="after")
    def check_llm_credentials(cls, values):
        """
        After loading all fields, ensure that if you choose openai you provided OPENAI_API_KEY,
        or if llama you provided LLAMA_MODEL_PATH.
        """
        backend = values.LLM_BACKEND.lower()
        if backend == "openai" and not values.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_BACKEND='openai'")
        if backend == "llama" and not values.LLAMA_MODEL_PATH:
            raise ValueError("LLAMA_MODEL_PATH is required when LLM_BACKEND='llama'")
        return values

# Instantiating this will now fail fast if any required field
# (or your chosen LLM credential) is missing.
settings = Settings()