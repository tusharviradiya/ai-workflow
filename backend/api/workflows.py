import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.agents.account_research.graph import build_account_research_graph

router = APIRouter()
graph = build_account_research_graph()

class AccountResearchRequest(BaseModel):
    query: str
    session_id: str

@router.post("/account-research")
async def run_account_research(request: AccountResearchRequest):
    start_time = time.time()
    
    # Initialize the state
    initial_state = {
        "user_query": request.query,
        "agents_used": [],
        "errors": []
    }
    
    try:
        # Run the workflow
        result = await graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    # Format the final dossier properly including agents trace at bottom
    final_dossier = result.get("final_dossier", "")
    agents_used = result.get("agents_used", [])
    
    dossier_with_trace = f"{final_dossier}\n\n→ Agents used: {', '.join(agents_used)}"
    
    return {
        "workflow": "account_research",
        "status": "completed",
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
                "proof_point": result.get("proof_point"),
                "recommended_way_in": "Recommend leading with how we modernized similar SaaS platforms, referencing the Doctoray case study."
            }
        },
        "errors": result.get("errors", [])
    }
