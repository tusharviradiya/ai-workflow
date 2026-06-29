from typing import TypedDict, Optional, List, Annotated
import operator

class OutreachState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────
    user_query: str                   # raw user input
    company_name: str                 # extracted from query
    prospect_name: Optional[str]      # if provided in query, e.g. "Sarah Chen"
    prospect_title: str               # e.g. "CTO", "VP Engineering"
    company_website: Optional[str]    # if provided

    # ── Session context (from Workflow 1 if available) ────────────────────
    prior_dossier: Optional[dict]     # full Workflow 1 output if session exists

    # ── Node 1 output ──────────────────────────────────────────────────────
    lead_trigger: str                 # the ONE trigger to anchor outreach on
    prospect_context: dict            # role, seniority, known priorities, tenure
    source: str                       # "prior_dossier" or "fresh_research"

    # ── Node 2 output ──────────────────────────────────────────────────────
    outreach_angle: str               # the specific framing for this prospect
    proof_point: str                  # case study name (from vector DB)
    proof_point_outcome: str          # one-line outcome, e.g. "14 weeks, blank page to prod"
    objection_to_preempt: str         # most likely objection for Touch 3
    win_themes: list[str]             # 2–3 win themes from strategist

    # ── Node 3 output ──────────────────────────────────────────────────────
    sequence_draft: list[dict]        # 5 touch objects (see schema in Section 4)

    # ── Node 4 output ──────────────────────────────────────────────────────
    qa_passed: bool
    qa_feedback: Optional[list[str]]  # specific issues with fix instructions (if failed)
    qa_notes: Optional[str]           # any warnings even on pass
    final_sequence: list[dict]        # approved sequence ready to return to UI
    retry_count: int                  # tracks Editor→Writer loops (max 1)

    # ── Meta ───────────────────────────────────────────────────────────────
    agents_used: Annotated[list[str], operator.add]            # for UI agent trace display
    errors: Annotated[list[str], operator.add]                 # non-fatal failures, logged and continued
