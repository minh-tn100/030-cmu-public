"""LangGraph assistant with skills: agent <-> ToolNode([load_skill]). Separate from the review pipeline on purpose (see agent/skills.py).
Usage: build(chat_model) with any LangChain chat model that supports bind_tools, e.g. init_chat_model("anthropic:claude-sonnet-5-5")."""
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from .skills import CATALOG, menu, as_tool

def build(llm, catalog: dict | None = None):
    tools = [as_tool()]
    system = f"Skills available (call load_skill before using one):\n{menu(catalog or CATALOG)}"
    bound = llm.bind_tools(tools)
    def agent(state: MessagesState):
        return {"messages": [bound.invoke([("system", system)] + state["messages"])]}
    g = StateGraph(MessagesState)
    g.add_node("agent", agent); g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "agent"); g.add_conditional_edges("agent", tools_condition); g.add_edge("tools", "agent")
    return g.compile()
