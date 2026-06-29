from typing import TypedDict, Optional, List, Annotated
import operator

class AccountResearchState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    user_query: str              # raw user input
    company_name: str            # extracted from query
    company_website: Optional[str]  # extracted if provided

    # ── Node 1 output ──────────────────────────────────────
    firmographics: dict          # industry, revenue, size, location, founded
    tech_stack: list[str]        # technologies identified via BuiltWith
    signals: list[str]           # buying signals: hiring, leadership, funding, news

    # ── Node 2 output ──────────────────────────────────────
    buying_committee: list[dict] # [{role, name_if_found, seniority, linkedin, note}]

    # ── Node 3 output ──────────────────────────────────────
    icp_score: int               # 0–100
    icp_tier: str                # "A", "B", or "C"
    icp_breakdown: dict          # per-criterion scores with pass/fail/partial
    pain_hypotheses: list[str]   # 2–3 hypotheses tied to Innvonix service lines
    proof_point: str             # best matching case study from vector DB

    # ── Node 4 output ──────────────────────────────────────
    final_dossier: str           # the formatted output shown to the user
    agents_used: Annotated[list[str], operator.add]  # agent names that executed, for UI trace display

    # ── Meta ───────────────────────────────────────────────
    errors: Annotated[list[str], operator.add]       # any tool call failures (non-blocking, log and continue)
