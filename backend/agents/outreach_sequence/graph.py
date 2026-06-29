from langgraph.graph import StateGraph, START, END
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import json
import os
from typing import Literal

from backend.agents.outreach_sequence.state import OutreachState
from backend.agents.outreach_sequence.tools import set_win_themes, map_objections, run_qa_checks
from backend.agents.account_research.tools import scan_signals, enrich_contacts, search_case_library

llm = ChatMistralAI(model="mistral-large-latest", temperature=0, timeout=120, max_retries=2)

# Models for structured outputs
class IntentResult(BaseModel):
    company_name: str
    prospect_title: str

class StrategyResult(BaseModel):
    outreach_angle: str
    proof_point: str
    proof_point_outcome: str
    objection_to_preempt: str

class SequenceDraftResult(BaseModel):
    touches: list[dict] = Field(description="List of 5 touch objects with touch_number, channel, day, subject, body, word_count, purpose")

def intent_router_node(state: OutreachState):
    """Parses user query to extract the company name and prospect title."""
    system_prompt = "Extract the company name and prospect title (e.g. CTO, CIO, VP Engineering) from the user's query."
    try:
        structured_llm = llm.with_structured_output(IntentResult)
        response = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_query"])
        ])
        return {
            "company_name": response.company_name,
            "prospect_title": response.prospect_title,
            "agents_used": ["intent_router"]
        }
    except Exception:
        # Fallback
        return {
            "company_name": state.get("company_name", "Unknown Company"),
            "prospect_title": state.get("prospect_title", "CIO"),
            "agents_used": ["intent_router"]
        }

def researcher_node(state: OutreachState):
    """Checks session context, falls back to fresh research if needed."""
    prior = state.get("prior_dossier")
    
    if prior and prior.get("company_name", "").lower() == state.get("company_name", "").lower():
        # Reuse existing research
        signals = prior.get("signals", [])
        lead_trigger = signals[0] if signals else "Company is expanding and adopting modern architectures."
        prospect_context = {"role": state.get("prospect_title")}
        for contact in prior.get("buying_committee", []):
            if state.get("prospect_title", "").lower() in contact.get("role", "").lower():
                prospect_context = contact
                break
        source = "prior_dossier"
    else:
        # Fresh research
        signals_res = scan_signals.invoke({"company_name": state.get("company_name")})
        contacts_res = enrich_contacts.invoke({"company_name": state.get("company_name")})
        
        lead_trigger = signals_res[0] if signals_res else "Recent growth and modernization."
        prospect_context = contacts_res[0] if contacts_res else {"role": state.get("prospect_title")}
        source = "fresh_research"

    return {
        "lead_trigger": lead_trigger,
        "prospect_context": prospect_context,
        "source": source,
        "agents_used": ["researcher"]
    }

def strategist_node(state: OutreachState):
    """Decides on the angle, proof point, and objection preemption."""
    trigger = state.get("lead_trigger")
    prospect_title = state.get("prospect_title")
    prospect_context = str(state.get("prospect_context", ""))
    
    # Tool: search_case_library
    proof_point_raw = search_case_library.invoke(f"{trigger} {prospect_title}")
    
    # Call LLM to structure the strategy based on the trigger and proof point
    system_prompt = f"""
    You are a BD Strategist.
    Prospect Role: {prospect_title}
    Context: {prospect_context}
    Trigger: {trigger}
    Proof Point Found: {proof_point_raw}
    
    DECISION 1: The Angle. Single strongest framing specific to the trigger.
    DECISION 2: The Proof Point & Outcome. Extract the name and outcome from the raw proof point.
    DECISION 3: The Objection Pre-empt. Single most likely pushback and response.
    """
    
    try:
        structured_llm = llm.with_structured_output(StrategyResult)
        res = structured_llm.invoke([SystemMessage(content=system_prompt)])
        angle = res.outreach_angle
        proof = res.proof_point
        outcome = res.proof_point_outcome
        objection = res.objection_to_preempt
    except Exception:
        angle = "Modernize legacy systems rapidly to support scale."
        proof = "Doctoray Case Study"
        outcome = "blank page to prod in 14 weeks"
        objection = "We already have an internal team."
        
    # Tools: set_win_themes
    win_themes = set_win_themes(trigger, proof, prospect_title)
    
    return {
        "outreach_angle": angle,
        "proof_point": proof,
        "proof_point_outcome": outcome,
        "objection_to_preempt": objection,
        "win_themes": win_themes,
        "agents_used": ["strategist"]
    }

def writer_node(state: OutreachState):
    """Drafts the 5 touches."""
    system_prompt = f"""
    You are an Outreach Writer. Write a 5-touch sequence.
    Trigger: {state.get("lead_trigger")}
    Angle: {state.get("outreach_angle")}
    Proof Point: {state.get("proof_point")} - Outcome: {state.get("proof_point_outcome")}
    Objection: {state.get("objection_to_preempt")}
    
    Follow the exact rules:
    Touch 1: Email (Day 0). Lead with trigger, proof point, soft ask, <90 words.
    Touch 2: LinkedIn (Day 2). <300 chars, reference trigger, no pitch.
    Touch 3: Email (Day 5). Pre-empt objection, second angle, <90 words.
    Touch 4: LinkedIn (Day 8). Share insight, no ask, <150 words.
    Touch 5: Email (Day 12). Pattern interrupt, clear breakup, <75 words.
    
    BANNED: quick call, just checking in, touch base, synergy.
    """
    
    if state.get("qa_feedback"):
        system_prompt += f"\n\nQA FEEDBACK RECEIVED (Fix only these): {state.get('qa_feedback')}\nCurrent Draft: {state.get('sequence_draft')}"

    try:
        structured_llm = llm.with_structured_output(SequenceDraftResult)
        res = structured_llm.invoke([SystemMessage(content=system_prompt)])
        draft = res.touches
    except Exception:
        # Fallback empty list on parser error, though Mistral is usually good
        draft = []
        
    return {
        "sequence_draft": draft,
        "agents_used": ["writer"]
    }

def editor_node(state: OutreachState):
    """Runs QA pass on the draft."""
    draft = state.get("sequence_draft", [])
    proof_point = state.get("proof_point", "")
    outcome = state.get("proof_point_outcome", "")
    win_themes = state.get("win_themes", [])
    
    qa_res = run_qa_checks(draft, proof_point, outcome, win_themes)
    
    passed = qa_res.get("passed", False)
    feedback = qa_res.get("feedback")
    
    return {
        "qa_passed": passed,
        "qa_feedback": feedback,
        "agents_used": ["editor"]
    }

def route_after_qa(state: OutreachState) -> Literal["writer", "end"]:
    if state.get("qa_passed"):
        state["final_sequence"] = state.get("sequence_draft", [])
        return "end"
    elif state.get("retry_count", 0) >= 1:
        state["qa_passed"] = True
        state["qa_notes"] = "QA failed on first pass. Sequence returned with issues flagged."
        state["final_sequence"] = state.get("sequence_draft", [])
        return "end"
    else:
        state["retry_count"] = state.get("retry_count", 0) + 1
        return "writer"

def build_outreach_graph():
    graph = StateGraph(OutreachState)
    
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("writer", writer_node)
    graph.add_node("editor", editor_node)
    
    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "researcher")
    graph.add_edge("researcher", "strategist")
    graph.add_edge("strategist", "writer")
    graph.add_edge("writer", "editor")
    
    graph.add_conditional_edges(
        "editor",
        route_after_qa,
        {
            "writer": "writer",
            "end": END
        }
    )
    
    return graph.compile()
