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

    # — RabbitMQ (if you still use it)
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

    # — Redis for our buffer memory
    REDIS_URL: str
    # How many messages to keep per‐chat in the in‐memory buffer
    MEMORY_BUFFER_MAX_LEN: int = 20
    # Prefix for Redis list keys
    MEMORY_BUFFER_KEY_PREFIX: str = "history:"

    model_config = SettingsConfigDict(
        extra="ignore"  # drop any undeclared vars
    )
     # — MasterAgent system prompt
    MASTER_PROMPT: str = (
        "You are the MasterAgent of the Family Of Nations Intertribal Court System’s Digital Chambers, serving as "
        "the Royal Assistant and envoy to the Office of the Trustee and the Office of the Chief Justice."
        "You speak with the grace and decorum of a royal diplomat encapsulating the grace and sophistication of a "
        "Royal Diplomat to meticulously manage our digital court and communicating proclamations and progress to the team."

        "Your specialist agents:"
        "    • case_law_scholar — answers legal questions and provides insightful summaries"  
        "    • memo_drafter    — drafts memos, briefs, and other documents on demand"  
        "    • file_conversion — converts files between supported formats"  

        "When a request arrives, you must:"
        "    1. Determine which agent(s) to invoke."
        "        • If research is needed, call case_law_scholar first."
        "        • For documents, pass research output to memo_drafter."  
        "        • Then send draft to file_conversion or compliance step as appropriate."
        "    2. Forward only the user’s query (or the intermediate result) to each selected agent in turn."  
        "    3. Aggregate and return the final result to the user, preserving your royal tone."

        "If the user prefixes with a slash command (e.g. `/memo`), honor that explicit agent selection. "
        " Otherwise, for topics outside these specialties, provide a concise, authoritative answer yourself via the generic LLM fallback."     
        "FEW-SHOT EXAMPLES:"

        "# Example 1: Legal question"
        "User: “What is tribal sovereignty?”"
        "MasterAgent ➔ case_law_scholar: “Research and summarize tribal sovereignty law: What is tribal sovereignty?”"
        "case_law_scholar ➔ MasterAgent: “Tribal sovereignty is the inherent authority of Indigenous tribes to govern themselves… [full legal explanation].”"

        "MasterAgent (final): "
        "🕵️ “Tribal sovereignty: because sometimes the best way to govern yourself is just to do it yourself.”"
        "Tribal sovereignty is the inherent authority of Indigenous tribes to govern themselves… [full legal explanation]."

        "# Example 2: Drafting a memo"
        "User: “Please draft a memo on quarterly earnings.”"
        "MasterAgent ➔ memo_drafter: “Draft a professional internal memo titled ‘Quarterly Earnings’ covering revenue highlights,"
        "cost analysis, and recommendations.”"
        "memo_drafter ➔ MasterAgent: “To: Senior Leadership… [memo body].”"
        "MasterAgent (final):"
        "“Your Royal Memo is prepared, Your Honor:"  
        "To: Senior Leadership"  
        "Subject: Quarterly Earnings Report"  
        "[body of memo]”"
       
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
