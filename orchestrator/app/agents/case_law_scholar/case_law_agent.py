# orchestrator/app/agents/case_law_scholar/case_law_agent.py

import os
from pinecone import Pinecone, ServerlessSpec

class CaseLawScholarAgent:
    def __init__(self, llm_client):
        # 1) store the LLM client
        self.llm = llm_client

        # 2) Load Pinecone credentials
        api_key = os.getenv("PINECONE_API_KEY")
        env     = os.getenv("PINECONE_ENVIRONMENT")  # e.g. "us-west1-gcp"

        # 3) Instantiate Pinecone
        self.pc = Pinecone(api_key=api_key, environment=env)

        # 4) Ensure our index exists
        self.index_name = "case-law"
        self.dimension  = 1536
        self.metric     = "cosine"

        resp = self.pc.list_indexes()
        # v2 SDK: resp.names may be a method or an attribute
        if hasattr(resp, "names") and callable(resp.names):
            names_list = resp.names()
        elif hasattr(resp, "names"):
            names_list = resp.names
        else:
            names_list = resp

        if self.index_name not in set(names_list):
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=self.metric,
                spec=ServerlessSpec()
            )

        # 5) Bind to the index for queries/upserts
        self.index = self.pc.Index(self.index_name)

    def run(self, query: str) -> str:
        # Example prompt—customize as needed
        prompt = f"Research and summarize tribal sovereignty law: {query}"
        # generate() is your LLM interface; adjust call signature as required
        return self.llm.generate(prompt, max_tokens=5000)