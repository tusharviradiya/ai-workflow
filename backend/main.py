from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from backend.api.workflows import router as workflows_router
from backend.api.workflows import run_account_research, AccountResearchRequest, run_outreach_sequence, OutreachRequest
import markdown
import json

app = FastAPI(title="IntelloNix AI Workforce")

app.include_router(workflows_router, prefix="/api/v1/workflows")

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IntelloNix AI Workforce</title>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .htmx-indicator{
                display:none;
            }
            .htmx-request .htmx-indicator{
                display:inline-block;
            }
            .htmx-request.htmx-indicator{
                display:inline-block;
            }
        </style>
    </head>
    <body class="bg-gray-900 text-gray-100 min-h-screen flex flex-col items-center p-10 font-sans">
        <div class="max-w-3xl w-full bg-gray-800 rounded-xl shadow-2xl overflow-hidden border border-gray-700">
            <div class="bg-indigo-600 p-6">
                <h1 class="text-3xl font-bold text-white tracking-tight">IntelloNix AI Workforce</h1>
                <p class="text-indigo-200 mt-2">Workflow 1: Account Research & ICP Scoring</p>
            </div>
            
            <div class="p-8">
                <form hx-post="/ui/research" hx-target="#results" hx-indicator="#loading" class="mb-8">
                    <label for="query" class="block text-sm font-medium text-gray-400 mb-2">Target Company</label>
                    <div class="flex gap-4">
                        <input type="text" id="query" name="query" placeholder="e.g. Research Bolt Nutritions" required 
                            class="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                        <button type="submit" 
                            class="bg-indigo-500 hover:bg-indigo-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-lg flex items-center justify-center min-w-[120px]">
                            <span class="htmx-indicator" id="loading">
                                <svg class="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            </span>
                            Research
                        </button>
                    </div>
                </form>
                
                <div id="results" class="bg-gray-900 rounded-lg p-6 border border-gray-700 min-h-[200px] flex items-center justify-center text-gray-500">
                    Your generated Account Dossier will appear here...
                </div>

                <form hx-post="/ui/outreach" hx-target="#outreach-results" hx-indicator="#outreach-loading" class="mb-8 mt-12 border-t border-gray-700 pt-8">
                    <label for="outreach-query" class="block text-sm font-medium text-gray-400 mb-2">Workflow 2: Personalised Outreach Sequence</label>
                    <div class="flex gap-4">
                        <input type="text" id="outreach-query" name="query" placeholder="e.g. Write outreach sequence for the CIO" required 
                            class="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                        <button type="submit" 
                            class="bg-indigo-500 hover:bg-indigo-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-lg flex items-center justify-center min-w-[120px]">
                            <span class="htmx-indicator" id="outreach-loading">
                                <svg class="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            </span>
                            Generate Sequence
                        </button>
                    </div>
                </form>
                
                <div id="outreach-results" class="bg-gray-900 rounded-lg p-6 border border-gray-700 min-h-[200px] flex items-center justify-center text-gray-500">
                    Your generated 5-touch sequence will appear here...
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/ui/research", response_class=HTMLResponse)
async def ui_research(query: str = Form(...)):
    try:
        req = AccountResearchRequest(query=query, session_id="htmx-session")
        # Run workflow
        result = await run_account_research(req)
        
        # Format the result nicely
        dossier = result["output"]["dossier"]
        html_dossier = markdown.markdown(dossier)
        
        agents = result["agents_used"]
        time_ms = result["execution_time_ms"]
        score = result["output"]["icp_score"]
        tier = result["output"]["icp_tier"]
        
        tier_color = "bg-green-500" if tier == "A" else "bg-yellow-500" if tier == "B" else "bg-red-500"
        
        return f"""
        <div class="animate-fade-in text-left w-full h-full text-gray-200">
            <div class="flex justify-between items-center mb-6 pb-4 border-b border-gray-700">
                <h2 class="text-xl font-semibold text-white">Research Results</h2>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">Execution: {time_ms}ms</span>
                    <span class="{tier_color} text-white text-xs font-bold px-3 py-1 rounded-full shadow-md">
                        ICP: {score}/100 (Tier {tier})
                    </span>
                </div>
            </div>
            
            <div class="prose prose-invert max-w-none prose-indigo leading-relaxed">
                {html_dossier}
            </div>
            
            <div class="mt-8 pt-4 border-t border-gray-700">
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">Agents Executed (Trace)</p>
                <div class="flex flex-wrap gap-2">
                    {''.join([f'<span class="px-2 py-1 bg-indigo-900/50 text-indigo-300 border border-indigo-700/50 rounded text-xs">{agent}</span>' for agent in agents])}
                </div>
            </div>
        </div>
        """
    except Exception as e:
        return f"""
        </div>
        """

@app.post("/ui/outreach", response_class=HTMLResponse)
async def ui_outreach(query: str = Form(...)):
    try:
        req = OutreachRequest(query=query, session_id="htmx-session")
        result = await run_outreach_sequence(req)
        
        touches_html = ""
        for touch in result["output"]["structured"]["sequence"]:
            touches_html += f"""
            <div class="bg-gray-800 border border-gray-600 rounded-lg p-4 mb-4 shadow-sm relative group">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex gap-2">
                        <span class="bg-indigo-900 text-indigo-200 text-xs px-2 py-1 rounded">Touch {touch.get('touch_number')}</span>
                        <span class="bg-gray-700 text-gray-300 text-xs px-2 py-1 rounded">{touch.get('channel', '').capitalize()}</span>
                        <span class="bg-gray-700 text-gray-300 text-xs px-2 py-1 rounded">Day {touch.get('day')}</span>
                    </div>
                </div>
                {f'<h4 class="font-bold text-white mb-2">{touch.get("subject", "")}</h4>' if touch.get('subject') else ''}
                <p class="text-gray-300 whitespace-pre-wrap">{touch.get('body', '')}</p>
            </div>
            """

        qa_badge = f'<span class="bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-md">✓ QA Passed</span>' if result.get("qa_passed") else f'<span class="bg-yellow-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-md">⚠ QA Issues Noted</span>'
        if result.get("qa_notes"):
            qa_badge += f' <span class="text-yellow-400 text-xs ml-2">⚠ {result.get("qa_notes")}</span>'
            
        agents = result["agents_used"]

        return f"""
        <div class="animate-fade-in text-left w-full h-full text-gray-200">
            <div class="flex justify-between items-center mb-6 pb-4 border-b border-gray-700">
                <h2 class="text-xl font-semibold text-white">5-Touch Outreach Sequence</h2>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">Source: {result.get('source')}</span>
                    {qa_badge}
                </div>
            </div>
            
            <div class="mb-4">
                <p class="text-sm text-gray-400">Prospect: <span class="text-white">{result["output"]["structured"]["prospect_title"]}</span> at <span class="text-white">{result["output"]["structured"]["company_name"]}</span></p>
                <p class="text-sm text-gray-400">Trigger: <span class="text-white">{result["output"]["structured"]["lead_trigger"]}</span></p>
                <p class="text-sm text-gray-400">Proof Point: <span class="text-white">{result["output"]["structured"]["proof_point"]} - {result["output"]["structured"]["proof_point_outcome"]}</span></p>
            </div>
            
            <div class="sequence-cards mt-6">
                {touches_html}
            </div>
            
            <div class="mt-8 pt-4 border-t border-gray-700">
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">Agents Executed (Trace)</p>
                <div class="flex flex-wrap gap-2">
                    {''.join([f'<span class="px-2 py-1 bg-indigo-900/50 text-indigo-300 border border-indigo-700/50 rounded text-xs">{agent}</span>' for agent in agents])}
                </div>
            </div>
        </div>
        """
    except Exception as e:
        import traceback
        return f"""
        <div class="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg">
            <h3 class="font-bold mb-2">Error during outreach generation</h3>
            <p class="text-sm">{str(e)}</p>
            <pre class="text-xs mt-2 overflow-x-auto">{traceback.format_exc()}</pre>
        </div>
        """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
