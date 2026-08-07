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
    news_sentiment: dict
    risk_analysis: dict

async def fetch_data_node(state: ReportState):
    print(f"Fetching data for funds {state['scheme_codes']}....")
    real_metrics = await fetch_multiple_fund_metrics(state['scheme_codes'])
    return {"metrics": real_metrics}

async def fetch_news_sentiment_node(state: ReportState):
    print("Fetching news sentiment (Placeholder)...")
    # TODO: Integrate with NewsAPI or Tavily for live sentiment
    dummy_sentiment = {str(code): "Positive" for code in state['scheme_codes']}
    return {"news_sentiment": dummy_sentiment}

async def fetch_risk_analysis_node(state: ReportState):
    print("Fetching risk analysis...")
    # TODO: Integrate with actual risk calculation endpoint
    dummy_risk = {str(code): {"volatility": "High", "beta": 1.2} for code in state['scheme_codes']}
    return {"risk_analysis": dummy_risk}

async def generate_report_node(state: ReportState, config: RunnableConfig):
    print("Generating detailed report using AI.....")
    metrics = state["metrics"]
    news = state.get("news_sentiment", {})
    risk = state.get("risk_analysis", {})
    system_prompt = f"""You are a strict, data driven mutual fund analyst.
    You have access to the following data:
    Metrics: {metrics}
    Recent News Sentiment: {news}
    Risk Analysis: {risk}
    
    RULES:
    - If the user asks to compare funds or write a report, write a detailed Markdown report incorporating the metrics, news sentiment, and risk profile.
    - If the user asks a follow up question(like "Which has higher risk?"), just answer their question concisely.
    - Format monetary values using Indian Financial notation.
    - If generating a full report, use Markdown tables and Mermaid.js pie chart for Sector Allocation.
    """
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm.ainvoke(messages, config=config)
    return {"messages": [response]}

builder = StateGraph(ReportState)
builder.add_node("fetch_data", fetch_data_node)
builder.add_node("fetch_news", fetch_news_sentiment_node)
builder.add_node("fetch_risk", fetch_risk_analysis_node)
builder.add_node("generate_report", generate_report_node)

builder.add_edge(START, "fetch_data")
# Run fetch_news and fetch_risk in parallel after fetch_data
builder.add_edge("fetch_data", "fetch_news")
builder.add_edge("fetch_data", "fetch_risk")
builder.add_edge("fetch_news", "generate_report")
builder.add_edge("fetch_risk", "generate_report")
builder.add_edge("generate_report", END)

report_workflow = builder.compile(
    checkpointer=memory,
)