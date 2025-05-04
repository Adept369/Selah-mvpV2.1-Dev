# orchestrator/app/orchestration/registry.py

from app.agents.case_law_scholar.case_law_agent import CaseLawScholarAgent
from app.agents.memo_drafter.memo_agent import MemoDrafterAgent
from app.agents.file_conversion_agent.file_conversion_agent import FileConversionAgent

def build_registry(llm_client):
    """
    Constructs the agent registry, injecting the shared LLM client.

    Returns:
        dict: Mapping of command/agent_key -> agent_instance
    """
    # instantiate each agent once
    case_agent = CaseLawScholarAgent(llm_client)
    memo_agent = MemoDrafterAgent(llm_client)
    file_conv  = FileConversionAgent(llm_client)

    return {
        # canonical keys
        "case_law_scholar": case_agent,
        "memo_drafter":     memo_agent,
        "file_conversion":  file_conv,

        # explicit slash-command aliases for case-law scholar
        "case":         case_agent,
        "law":          case_agent,
        "sovereignty":  case_agent,
        "case_law":     case_agent,
        "precedent":    case_agent,

        # explicit slash-command aliases for memo drafter
        "memo":         memo_agent,
        "draft":        memo_agent,
        "memo_draft":   memo_agent,

        # explicit slash-command aliases for file conversion
        "convert":      file_conv,
        "convert_file": file_conv,
        "file":         file_conv,
        "csv_to_xlsx":  file_conv,
        "xlsx_to_csv":  file_conv,
        "pdf_to_docx":  file_conv,
    }
