from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import uuid

from backend.agents.account_research.graph import build_account_research_graph
from backend.agents.outreach_sequence.graph import build_outreach_graph

router = APIRouter()
account_graph = build_account_research_graph()
outreach_graph = build_outreach_graph()

# In-memory session store for MVP
SESSION_STORE = {}

class AccountResearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class OutreachRequest(BaseModel):
    query: str
    session_id: str
    prospect_title: Optional[str] = None
    company_name: Optional[str] = None

@router.post("/account-research")
async def run_account_research(request: AccountResearchRequest):
    start_time = time.time()
    
    session_id = request.session_id or str(uuid.uuid4())
    
    initial_state = {
        "user_query": request.query,
        "agents_used": [],
        "errors": []
    }
    
    try:
        result = await account_graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    final_dossier = result.get("final_dossier", "")
    agents_used = result.get("agents_used", [])
    
    dossier_with_trace = f"{final_dossier}\n\n→ Agents used: {', '.join(agents_used)}"
    
    # Save to session store
    SESSION_STORE[session_id] = {
        "last_workflow": "account_research",
        "company_name": result.get("company_name"),
        "firmographics": result.get("firmographics", {}),
        "signals": result.get("signals", []),
        "buying_committee": result.get("buying_committee", []),
        "icp_score": result.get("icp_score"),
        "icp_tier": result.get("icp_tier"),
        "pain_hypotheses": result.get("pain_hypotheses", []),
        "proof_point": result.get("proof_point"),
        "final_dossier": final_dossier
    }
    
    return {
        "workflow": "account_research",
        "status": "completed",
        "session_id": session_id,
        "agents_used": agents_used,
        "execution_time_ms": execution_time_ms,
        "output": {
            "dossier": dossier_with_trace,
            "icp_score": result.get("icp_score"),
            "icp_tier": result.get("icp_tier"),
            "structured": {
                "company_name": result.get("company_name"),
                "industry": result.get("firmographics", {}).get("industry"),
                "revenue_band": result.get("firmographics", {}).get("revenue_band"),
                "location": result.get("firmographics", {}).get("location"),
                "icp_score": result.get("icp_score"),
                "icp_tier": result.get("icp_tier"),
                "signals": result.get("signals", []),
                "buying_committee": result.get("buying_committee", []),
                "pain_hypotheses": result.get("pain_hypotheses", []),
                "proof_point": result.get("proof_point")
            }
        },
        "errors": result.get("errors", [])
    }

@router.post("/outreach-sequence")
async def run_outreach_sequence(request: OutreachRequest):
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
        
    start_time = time.time()
    
    prior_dossier = SESSION_STORE.get(request.session_id)
    
    initial_state = {
        "user_query": request.query,
        "company_name": request.company_name or "",
        "prospect_title": request.prospect_title or "",
        "prior_dossier": prior_dossier,
        "retry_count": 0,
        "agents_used": [],
        "errors": []
    }
    
    try:
        result = await outreach_graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    # Format sequence
    seq = result.get("final_sequence", [])
    formatted_seq = f"5-TOUCH OUTREACH SEQUENCE\n\nProspect: {result.get('prospect_title')} · {result.get('company_name')}\nTrigger: {result.get('lead_trigger')}\n\n"
    for touch in seq:
        formatted_seq += f"──────────────────────────────────────────\n"
        formatted_seq += f"Touch {touch.get('touch_number')} — {touch.get('channel')} (Day {touch.get('day')})\n"
        if touch.get('subject'):
            formatted_seq += f"Subject: {touch.get('subject')}\n\n"
        formatted_seq += f"{touch.get('body')}\n"
    
    formatted_seq += f"──────────────────────────────────────────\n"
    formatted_seq += f"Proof point used: {result.get('proof_point')} - {result.get('proof_point_outcome')}\n"
    formatted_seq += f"Spam / tone check: {'PASSED' if result.get('qa_passed') else 'FAILED'}\n"
    if result.get("qa_notes"):
        formatted_seq += f"⚠ {result.get('qa_notes')}\n"
        
    formatted_seq += f"\n→ Agents used: {', '.join(result.get('agents_used', []))}\n"
    formatted_seq += f"→ Source: {result.get('source')}"
    
    return {
        "workflow": "outreach_sequence",
        "status": "completed",
        "agents_used": result.get("agents_used", []),
        "execution_time_ms": execution_time_ms,
        "source": result.get("source"),
        "qa_passed": result.get("qa_passed", False),
        "qa_notes": result.get("qa_notes"),
        "output": {
            "formatted_sequence": formatted_seq,
            "structured": {
                "prospect_title": result.get("prospect_title"),
                "company_name": result.get("company_name"),
                "lead_trigger": result.get("lead_trigger"),
                "proof_point": result.get("proof_point"),
                "proof_point_outcome": result.get("proof_point_outcome"),
                "sequence": seq
            }
        },
        "errors": result.get("errors", [])
    }
