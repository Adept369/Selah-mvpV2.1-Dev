# orchestrator/app/agents/memo_drafter/memo_agent.py

import os
from pinecone import Pinecone, ServerlessSpec

class MemoDrafterAgent:
    def __init__(self, llm_client):
        # 1) store your LLM client
        self.llm = llm_client

        # 2) Load Pinecone credentials
        api_key = os.getenv("PINECONE_API_KEY")
        env     = os.getenv("PINECONE_ENVIRONMENT")  # e.g. "us-west1-gcp"

        # 3) Instantiate Pinecone
        self.pc = Pinecone(api_key=api_key, environment=env)

        # 4) Ensure our index exists
        self.index_name = "memo-drafter"
        resp = self.pc.list_indexes()
        # v2 SDK: resp.names may be a method or attribute
        if hasattr(resp, "names") and callable(resp.names):
            names_list = resp.names()
        elif hasattr(resp, "names"):
            names_list = resp.names
        else:
            names_list = resp

        if self.index_name not in set(names_list):
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec()  # adjust cloud/region here if you need serverless spec args
            )

        # 5) Bind to the index for use
        self.index = self.pc.Index(self.index_name)

    def run(self, query: str) -> str:
        # TODO: implement your memo‐draft logic using self.index and self.llm
        prompt = f"Draft a professional memo based on: {query}"
        return self.llm.generate(prompt, max_tokens=5000)