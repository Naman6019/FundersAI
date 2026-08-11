from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from service import fetch_multiple_fund_metrics
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

load_dotenv()

memory = MemorySaver()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class ReportState(MessagesState):
    scheme_codes: list[int]
    metrics: dict

async def fetch_data_node(state: ReportState):
    print(f"Fetching data for funds {state['scheme_codes']}....")
    real_metrics = await fetch_multiple_fund_metrics(state['scheme_codes'])
    return {"metrics": real_metrics}

async def generate_report_node(state: ReportState, config: RunnableConfig):
    print("Generating detailed report using AI.....")
    metrics = state["metrics"]

    # Risk figures (alpha, beta, sharpe_ratio, risk_level) come straight from
    # mutual_fund_core_snapshot in `metrics[code]["core"]" — the same
    # official-document-backed table the rest of the app uses. There used to
    # be a separate "risk analysis" step here that fabricated
    # {"volatility": "High", "beta": 1.2} for every single fund regardless of
    # its actual data; that's gone. We only ever hand the model numbers that
    # actually came from a stored source.
    system_prompt = f"""You are a strict, data driven mutual fund analyst.
    You have access to the following data, sourced from FundersAI's mutual fund
    database (official AMC factsheets/disclosures and AMFI/MFAPI NAV data):
    Metrics: {metrics}

    RULES:
    - Only state facts that are present in the Metrics data above. Risk figures
      (alpha, beta, sharpe_ratio, risk_level) are inside each fund's "core" entry.
    - You do NOT have access to live news or sentiment data. If asked about news,
      sentiment, or anything not present in Metrics, say plainly that you don't
      have that data rather than guessing or inventing a value.
    - If a field is missing or null for a fund, say it's not available for that
      fund instead of estimating or assuming a typical value.
    - If the user asks to compare funds or write a report, write a detailed
      Markdown report incorporating the metrics and risk profile from the data above.
    - If the user asks a follow up question (like "Which has higher risk?"), just
      answer their question concisely using the data above.
    - Format monetary values using Indian Financial notation.
    - If generating a full report, use Markdown tables and a Mermaid.js pie chart
      for Sector Allocation.
    """
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm.ainvoke(messages, config=config)
    return {"messages": [response]}

builder = StateGraph(ReportState)
builder.add_node("fetch_data", fetch_data_node)
builder.add_node("generate_report", generate_report_node)

builder.add_edge(START, "fetch_data")
builder.add_edge("fetch_data", "generate_report")
builder.add_edge("generate_report", END)

report_workflow = builder.compile(
    checkpointer=memory,
)
