from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from app.services.report_service import fetch_fund_metrics
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model = "gpt-4o-mini", temperature = 0)

class ReportState(TypedDict):
    scheme_code: int
    metrics: dict | None
    final_report: str | None

async def fetch_data_node(state: ReportState):
    print(f"Fetching data for fund {state['scheme_code']}....")
    real_metrics = await fetch_fund_metrics(state['scheme_code'])
    return {"metrics": real_metrics}

async def generate_report_node(state: ReportState):
    print("Generating detailed report using AI.....")
    metrics = state["metrics"]
    system_prompt = """You are a strict, data-driven mutual fund analyst.
    You will be provided with a JSON dictionary containing a mutual fund's core metrics, top 10 holdings, and sector allocation.
    Write a detailed, professional investment report analyzing the fund's performance and portfolio.
    
    RULES:
    - Do NOT invent any data. Only use the provided metrics.
    - If the expense_ratio is higher than 1.5, include a warning.
    - If the provided 'fund_manager' is recent, you MUST add a specific paragraph analyzing whether the 1-year returns reflect the new manager's strategy or the old manager's legacy.
    - FORMATTING: All monetary values MUST be formatted using standard Indian financial notation (e.g., "₹896.3 Crores"). Do not awkwardly combine the ₹ symbol with the word "million".
    - RISK-O-METER: You must explicitly state the fund's risk level based on the provided `risk_level` field in a prominent callout.
    - SECTOR ALLOCATION PIE CHART: You MUST generate a Mermaid.js pie chart using the provided sector allocation data. Wrap the pie chart in ```mermaid ... ``` code blocks.
    - TOP HOLDINGS: You MUST display the provided top holdings in a clean, perfectly aligned Markdown table (Columns: Security Name, Sector, Weight %).
    - Format the output in Markdown with headers: Overview, Portfolio & Sectors, Performance, Verdict.
    """

    user_prompt = f"Please analyize this fund:\n{metrics}"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    return {"final_report": response.content}

builder = StateGraph(ReportState)

builder.add_node("fetch_data", fetch_data_node)
builder.add_node("generate_report", generate_report_node)

builder.add_edge(START, "fetch_data")
builder.add_edge("fetch_data", "generate_report")
builder.add_edge("generate_report", END)

report_workflow = builder.compile()