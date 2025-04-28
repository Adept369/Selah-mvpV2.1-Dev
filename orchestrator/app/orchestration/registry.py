# orchestrator/app/orchestration/registry.py

from app.agents.case_law_scholar.case_law_agent import CaseLawScholarAgent

def build_registry(llm_client) -> dict[str, CaseLawScholarAgent]:
    """
    Constructs the agent registry for MVP v2, only including the
    CaseLawScholarAgent for legal research queries.
    """
    return {
        "case_law_scholar": CaseLawScholarAgent(llm_client),
    }