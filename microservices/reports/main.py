from fastapi.exceptions import ResponseValidationError
from fastapi import FastAPI
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from report_graph import report_workflow
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import json
import sys

app = FastAPI(title="Report AI Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows connection from Next.js on Vercel and local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Report AI Microservice"}

class ReportRequest(BaseModel):
    scheme_codes: list[int] = Field(max_length=4, description="List up to 4 fund scheme codes")
    thread_id: str = Field(description="Unique ID for this chat session")
    user_message: str = Field(description="The user's prompt or question")

@app.post("/api/v1/reports/chat")
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
@app.post("/api/v1/reports/stream")
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
    html: str = Field(description="The pre-rendered HTML content of the report")

@app.post("/api/v1/reports/pdf")
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
        page = browser.new_page()
        
        # Load the HTML content directly
        page.set_content(wrapped_html, wait_until="networkidle")
        
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