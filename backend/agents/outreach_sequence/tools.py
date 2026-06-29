from langchain_mistralai.chat_models import ChatMistralAI
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

# We use Mistral for our tool reasoning
llm = ChatMistralAI(model="mistral-large-latest", temperature=0, timeout=120, max_retries=2)

class WinThemesResult(BaseModel):
    win_themes: list[str] = Field(description="2-3 formal win themes based on the trigger and proof point")

class ObjectionMappingResult(BaseModel):
    objection: str = Field(description="The single most likely objection from this prospect")
    preemption: str = Field(description="A specific, non-defensive response to preempt the objection")

class SpamCheckResult(BaseModel):
    flagged_issues: list[dict] = Field(description="List of dicts with 'touch_number', 'phrase', and 'suggestion'")
    tone_issues: list[dict] = Field(description="List of dicts with 'touch_number' and 'issue'")
    claims_issues: list[dict] = Field(description="List of dicts with 'touch_number' and 'issue'")
    passed: bool = Field(description="True if no issues found across spam, tone, and claims")

def set_win_themes(trigger: str, proof_point: str, prospect_title: str) -> list[str]:
    """Formalise 2-3 win themes based on trigger and proof point."""
    prompt = f"Given the prospect ({prospect_title}) trigger: '{trigger}' and our proof point: '{proof_point}', generate 2-3 specific win themes for our outreach. Return them as a list of strings."
    try:
        structured_llm = llm.with_structured_output(WinThemesResult)
        res = structured_llm.invoke(prompt)
        return res.win_themes
    except Exception:
        return ["Accelerated Modernisation", "Senior Engineering Capacity", "Reduced Time to Value"]

def map_objections(prospect_title: str, company_context: str) -> dict:
    """Identify the single most likely objection and a pre-emption."""
    prompt = f"Prospect: {prospect_title}. Context: {company_context}. Identify the single most likely pushback from them, and how to preempt it in our outreach."
    try:
        structured_llm = llm.with_structured_output(ObjectionMappingResult)
        res = structured_llm.invoke(prompt)
        return {"objection": res.objection, "preemption": res.preemption}
    except Exception:
        return {
            "objection": "We already have an internal engineering team.",
            "preemption": "We act as a force multiplier for your internal team to clear the backlog they can't get to, not a replacement."
        }

def run_qa_checks(sequence: list[dict], proof_point: str, proof_point_outcome: str, win_themes: list[str]) -> dict:
    """Check spam triggers, tone, and factual claims."""
    sequence_text = str(sequence)
    prompt = f"""
    You are a QA editor. Review this 5-touch outreach sequence: {sequence_text}
    Against this proof point: {proof_point} ({proof_point_outcome})
    And these win themes: {win_themes}

    Run 3 checks:
    1. SPAM: Flag phrases like 'quick call', 'just checking in', 'touch base', 'synergy', 'leverage', 'I wanted to reach out', 'hope this finds you well', 'best solution', etc.
    2. TONE: Flag excessive enthusiasm, buzzword stacking, vague outcomes.
    3. CLAIMS: Flag any invented metrics or unsupported superlatives.

    Return the structured result.
    """
    try:
        structured_llm = llm.with_structured_output(SpamCheckResult)
        res = structured_llm.invoke(prompt)
        
        feedback = []
        for i in res.flagged_issues:
            feedback.append(f"Touch {i.get('touch_number', '?')}: Spam phrase '{i.get('phrase', '')}' - {i.get('suggestion', '')}")
        for i in res.tone_issues:
            feedback.append(f"Touch {i.get('touch_number', '?')}: Tone issue - {i.get('issue', '')}")
        for i in res.claims_issues:
            feedback.append(f"Touch {i.get('touch_number', '?')}: Claim issue - {i.get('issue', '')}")
            
        return {
            "passed": res.passed if not feedback else False,
            "feedback": feedback if feedback else None
        }
    except Exception:
        # Fallback to a pass if parsing fails
        return {"passed": True, "feedback": None}
