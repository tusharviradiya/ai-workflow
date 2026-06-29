from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import json
import os
from dotenv import load_dotenv

load_dotenv()

from backend.agents.account_research.state import AccountResearchState
from backend.agents.account_research.tools import (
    pull_firmographics,
    scan_signals,
    enrich_contacts,
    apply_icp_filters,
    search_case_library,
)

from langchain_mistralai.chat_models import ChatMistralAI

llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

def intent_router_node(state: AccountResearchState):
    """Parses user query to extract the company name."""
    system_prompt = "Extract the company name from the user's query. Return ONLY the company name as plain text. If you cannot find one, reply 'UNKNOWN'."
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_query"])
    ])
    company_name = response.content.strip()
    return {"company_name": company_name}

def researcher_signals_node(state: AccountResearchState):
    """Gather firmographics and signals."""
    company_name = state.get("company_name", "")
    
    # In a real agent, we'd use tool binding, but since we are mocking:
    # Let's call the tools directly for simplicity and deterministic output
    # or we can use an agent executor. For MVP reliability, we'll invoke tools.
    
    try:
        firmo_res = pull_firmographics.invoke({"company_name": company_name})
    except Exception as e:
        firmo_res = {}
        
    try:
        signals_res = scan_signals.invoke({"company_name": company_name, "lookback_days": 90})
    except Exception as e:
        signals_res = []
        
    return {
        "firmographics": firmo_res,
        "signals": signals_res,
        "agents_used": ["researcher_signals"]
    }

def researcher_people_node(state: AccountResearchState):
    """Gather buying committee."""
    company_name = state.get("company_name", "")
    
    try:
        contacts_res = enrich_contacts.invoke({"company_name": company_name})
    except Exception as e:
        contacts_res = []
        
    return {
        "buying_committee": contacts_res,
        "agents_used": ["researcher_people"]
    }

def icp_qualifier_node(state: AccountResearchState):
    """Score the account against ICP and find pain hypotheses and proof points."""
    firmographics = state.get("firmographics", {})
    signals = state.get("signals", [])
    
    try:
        icp_res = apply_icp_filters.invoke({"firmographics": firmographics, "signals": signals})
    except Exception as e:
        icp_res = {"score": 0, "tier": "C", "breakdown": {}}
        
    try:
        proof_point = search_case_library.invoke({"query": f"Match case study for {firmographics.get('industry', 'tech')} using cloud and AI"})
    except Exception as e:
        proof_point = "Not found"
        
    system_prompt = f"""You are an ICP Qualification Specialist at Innvonix.
You have the following firmographics: {json.dumps(firmographics)}
Signals: {json.dumps(signals)}

Generate 2 pain hypotheses mapped to Innvonix service lines based on this data. 
Format as a JSON array of strings. ONLY RETURN JSON."""
    
    pain_hypotheses = []
    try:
        response = llm.invoke([SystemMessage(content=system_prompt)])
        # Parse JSON
        content = response.content.strip().replace("```json", "").replace("```", "")
        pain_hypotheses = json.loads(content)
    except Exception as e:
        pass
        
    return {
        "icp_score": icp_res.get("score", 0),
        "icp_tier": icp_res.get("tier", "C"),
        "icp_breakdown": icp_res.get("breakdown", {}),
        "pain_hypotheses": pain_hypotheses,
        "proof_point": proof_point,
        "agents_used": ["icp_qualifier"]
    }

def writer_node(state: AccountResearchState):
    """Produce the final Account Dossier."""
    system_prompt = f"""You are a BD Strategy Writer at Innvonix.
Write a 200-word Account Dossier in EXACTLY this format:

ACCOUNT DOSSIER & FIT SCORE

Account:  [Company Name]  ·  [Industry]  ·  ~[Revenue]  ·  [Location]
ICP fit:  [Score] / 100  ([Tier] tier)

Signals worth acting on
• [Signal 1]
• [Signal 2]
• [Signal 3]

Buying committee
• Economic buyer:   [Role title]  ([note])
• Technical buyer:  [Role title]  ([note])
• Influencer:       [Role title]  ([note])

Pain hypotheses (tied to Innvonix service lines)
1. [Hypothesis 1]
2. [Hypothesis 2]

Recommended way in
[1-2 sentences referencing the proof point]

---
State Data:
Company: {state.get("company_name")}
Firmographics: {json.dumps(state.get("firmographics", {}))}
Signals: {json.dumps(state.get("signals", []))}
Buying Committee: {json.dumps(state.get("buying_committee", []))}
ICP Score: {state.get("icp_score", 0)}
ICP Tier: {state.get("icp_tier", "C")}
Pain Hypotheses: {json.dumps(state.get("pain_hypotheses", []))}
Proof Point: {state.get("proof_point", "Not found")}

Return ONLY the formatted dossier. Do not include markdown code block wrappers.
"""
    response = llm.invoke([SystemMessage(content=system_prompt)])
    
    final_dossier = response.content.strip()
    
    return {
        "final_dossier": final_dossier,
        "agents_used": ["writer"]
    }

def build_account_research_graph():
    graph = StateGraph(AccountResearchState)

    graph.add_node("intent_router", intent_router_node)
    graph.add_node("researcher_signals", researcher_signals_node)
    graph.add_node("researcher_people", researcher_people_node)
    graph.add_node("icp_qualifier", icp_qualifier_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "researcher_signals")
    graph.add_edge("intent_router", "researcher_people")
    graph.add_edge("researcher_signals", "icp_qualifier")
    graph.add_edge("researcher_people", "icp_qualifier")
    graph.add_edge("icp_qualifier", "writer")
    graph.add_edge("writer", END)

    return graph.compile()
