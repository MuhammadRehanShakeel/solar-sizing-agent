"""
graph.py - The agent itself, built with LangGraph.

    START -> [agent] --wants a tool?--> [tools] --result--> [agent] -> ... -> END
                   +--no, has an answer------------------------------------> END

[agent] = the language model. It reads the chat and either answers or asks for tools.
[tools] = runs the requested Python tools (tools.py) and gives the results back.
The loop repeats until the model answers in plain text (max config.MAX_AGENT_STEPS rounds).
"""
import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app import config
from app.agent import llm as llm_module
from app.agent.prompts import build_system_prompt
from app.agent.tools import make_tools
from app.services import sizing

log = logging.getLogger("agent")


def build_graph(model, tools):
    """model: a chat model with the tools bound. Returns the compiled LangGraph app."""
    def agent(state: MessagesState):
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)         # tool call -> "tools", answer -> END
    graph.add_edge("tools", "agent")
    return graph.compile()


def _model_name(message) -> str:
    meta = getattr(message, "response_metadata", {}) or {}
    return meta.get("model_name") or meta.get("model") or "unknown"


def run_agent(ctx: dict, earlier: list, user_text: str, bill_data=None, export_rate=11.0, model=None) -> dict:
    """
    One customer message in, one answer out.
      ctx      : shared dict (session_id, quote, lead) - tools write into it
      earlier  : previous messages [{"role": "user"/"assistant", "content": ...}] (oldest first)
      model    : only for tests (a fake model); normally chosen in llm.py
    """
    tools = make_tools(ctx)
    quote = ctx.get("quote")
    system = build_system_prompt(config.INSTALLER_NAME, export_rate,
                                 json.dumps(bill_data) if bill_data else None,
                                 json.dumps({**sizing.summary(quote["result"]), "quote_link": quote["url"]})
                                 if quote else None,
                                 location="shared" if ctx.get("location") else None)
    messages = [SystemMessage(system)]
    for m in earlier:
        if m["role"] == "user":
            messages.append(HumanMessage(m["content"]))
        elif m["role"] == "assistant":
            messages.append(AIMessage(m["content"]))
    messages.append(HumanMessage(user_text))

    app = build_graph(model or llm_module.chat_model(tools), tools)
    try:
        state = app.invoke({"messages": messages}, {"recursion_limit": config.MAX_AGENT_STEPS * 2 + 1})
    except GraphRecursionError:
        log.warning("Agent needed too many steps")
        return {"reply": "Sorry, I got stuck working that out. Could you tell me your monthly units and city again?",
                "tools_used": [], "model": None, "tool_results": []}

    new = state["messages"][len(messages):]
    tools_used = [m.name for m in new if isinstance(m, ToolMessage)]
    answer = next((m for m in reversed(new) if isinstance(m, AIMessage) and m.text.strip()), None)
    reply = answer.text.strip() if answer else "Sorry, I could not answer that. Please try again."
    return {"reply": reply, "tools_used": tools_used, "model": _model_name(answer) if answer else None,
            "tool_results": [{"tool": m.name, "content": m.content} for m in new if isinstance(m, ToolMessage)]}
