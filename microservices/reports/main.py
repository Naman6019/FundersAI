from fastapi.exceptions import ResponseValidationError
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from report_graph import report_workflow
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
from rate_limit import check_rate_limit, client_identifier_from_headers, rate_limit_headers
import hmac
import json
import os
import sys

app = FastAPI(title="Report AI Microservice")

# Only our own Next.js server (fundersai.co.in / synthesis.fundersai.co.in / local dev)
# ever needs to call this service directly. No browser should be hitting these origins
# with credentials, so keep the allow-list explicit and credentials off.
ALLOWED_ORIGINS = [
    "https://fundersai.co.in",
    "https://www.fundersai.co.in",
    "https://synthesis.fundersai.co.in",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def authorize_reports_request(
    x_internal_proxy_key: str | None = Header(default=None, alias="X-Internal-Proxy-Key"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_tier: str | None = Header(default=None, alias="X-User-Tier"),
    x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For"),
) -> None:
    """Same auth model as the main research chat endpoint
    (backend/app/services/chat_service.py::chat_endpoint): the Next.js server
    verifies the user's Supabase session and forwards X-User-Id/X-User-Tier,
    signed with a shared X-Internal-Proxy-Key so only that server can set them.

    Unlike /api/chat (where the proxy key is optional, used only to gate usage
    accounting), we require it here and require a logged-in user — report
    generation is expensive (LLM + headless-browser PDF render) and was
    previously reachable by anyone, unauthenticated.
    """
    expected = os.getenv("REPORTS_INTERNAL_PROXY_KEY", "").strip()
    if not expected or not x_internal_proxy_key or not hmac.compare_digest(x_internal_proxy_key, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid internal proxy credentials")
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing authenticated user context")

    # Trusted now that the proxy key has been verified: rate-limit per logged-in
    # user (matches how billing tiers work elsewhere) rather than per-IP, so it
    # can't be trivially bypassed by rotating IPs, and falls back to IP only if
    # the caller somehow omitted the user id.
    identity = client_identifier_from_headers(x_user_id or x_forwarded_for)
    result = await check_rate_limit("reports", identity)
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many report requests. Please wait before generating another report.",
            headers=rate_limit_headers(result),
        )


@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Report AI Microservice"}

class ReportRequest(BaseModel):
    scheme_codes: list[int] = Field(max_length=4, description="List up to 4 fund scheme codes")
    thread_id: str = Field(description="Unique ID for this chat session")
    user_message: str = Field(max_length=2000, description="The user's prompt or question")

@app.post("/api/v1/reports/chat", dependencies=[Depends(authorize_reports_request)])
async def chat_with_report(request: ReportRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    result = await report_workflow.ainvoke({
        "scheme_codes": request.scheme_codes,
        "messages": [HumanMessage(content = request.user_message)]
    }, config=config)
    ai_response = result["messages"][-1].content
    return {
        "status": "success",
        "thread_id": request.thread_id,
        "response": ai_response
    }
@app.post("/api/v1/reports/stream", dependencies=[Depends(authorize_reports_request)])
async def chat_with_stream_response(request: ReportRequest):
    async def generate_events():
        config = {"configurable": {"thread_id": request.thread_id}}
        yield f"data: {json.dumps({'status': 'started'})}\n\n"
        async for msg, metadata in report_workflow.astream(
            {
                "scheme_codes": request.scheme_codes,
            "messages": [HumanMessage(content=request.user_message)]
            },
            config = config,
            stream_mode="messages"
        ):
            if msg.content and metadata.get("langgraph_node") == "generate_report":
                chunk = {"text": msg.content}
                yield f"data: {json.dumps(chunk)}\n\n"
        yield f"data: {json.dumps({'status': 'completed'})}\n\n"
    return StreamingResponse(generate_events(), media_type="text/event-stream")

class PDFRequest(BaseModel):
    html: str = Field(max_length=200_000, description="The pre-rendered HTML content of the report")

@app.post("/api/v1/reports/pdf", dependencies=[Depends(authorize_reports_request)])
def generate_pdf(request: PDFRequest):
    html_content = request.html
    
    # Wrap the HTML in a basic template to give it some padding and a light theme for PDF
    wrapped_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background: #fff;
                margin: 0;
                padding: 0;
            }}
            h1, h2, h3, h4 {{ color: #111; margin-top: 1.5em; margin-bottom: 0.5em; }}
            h1 {{ font-size: 24px; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h2 {{ font-size: 20px; }}
            h3 {{ font-size: 18px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
            th, td {{ border: 1px solid #dfe2e5; padding: 8px 12px; text-align: left; }}
            th {{ background-color: #f6f8fa; font-weight: 600; }}
            ul {{ padding-left: 2em; }}
            li {{ margin-bottom: 0.25em; }}
            svg {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # html is the innerHTML of a rendered report — ultimately sourced from
        # an LLM response (markdown -> ReactMarkdown -> DOM). Markdown image
        # syntax alone is enough to smuggle an <img src="http://169.254.169.254/...">
        # into that HTML, which a full-featured headless browser would happily
        # fetch server-side (SSRF, incl. cloud instance-metadata exfiltration).
        # Nothing in a legitimate report needs to load an external resource —
        # charts are already inline SVG — so we disable JS and hard-block any
        # network request that isn't a data: URI.
        page = browser.new_page(java_script_enabled=False)

        def _block_external_requests(route):
            url = route.request.url
            if url.startswith("data:") or url == "about:blank":
                route.continue_()
            else:
                route.abort()

        page.route("**/*", _block_external_requests)

        # Load the HTML content directly
        page.set_content(wrapped_html, wait_until="load", timeout=15_000)

        # Generate PDF
        pdf_bytes = page.pdf(
            format="Letter",
            margin={"top": "40px", "right": "40px", "bottom": "40px", "left": "40px"},
            print_background=True
        )
        browser.close()
        
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=fundersai-report.pdf"
    })