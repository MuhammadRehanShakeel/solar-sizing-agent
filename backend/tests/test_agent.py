"""The LangGraph agent with a scripted (pretend) model: tests the loop, the tools and the guard rails."""
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.agent import tools as tools_module
from app.agent.graph import run_agent
from tests.conftest import ScriptedModel, tool_call


def model(*script):
    return ScriptedModel(script=list(script), seen=[])


def test_agent_calls_the_calculator_then_answers(fake_db):
    m = model(tool_call("calculate_solar_options", {"monthly_units": [500], "city": "Islamabad"}),
              AIMessage("A 5.85 kW on-grid system is best for you."))
    ctx = {"session_id": "a" * 32}
    out = run_agent(ctx, [], "My bill is 500 units, Islamabad", model=m)
    assert out["reply"].startswith("A 5.85 kW")
    assert out["tools_used"] == ["calculate_solar_options"]
    assert out["model"] == "scripted-test-model"
    assert ctx["quote"]["result"]["recommended"] == "on_grid"
    assert fake_db.ran("INSERT INTO Quotes")
    tool_result = [msg for msg in m.seen[1] if isinstance(msg, ToolMessage)][0]
    assert "quote_link" in tool_result.content and "\"months\":" not in tool_result.content


def test_history_bill_and_latest_quote_reach_the_model(fake_db):
    m = model(AIMessage("Sure."))
    ctx = {"session_id": "a" * 32}
    run_agent(ctx, [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Salam!"}], "next",
              bill_data={"average_units": 412}, model=m)
    system = m.seen[0][0]
    assert isinstance(system, SystemMessage) and "412" in system.content
    assert [type(x).__name__ for x in m.seen[0]] == ["SystemMessage", "HumanMessage", "AIMessage", "HumanMessage"]


def test_bad_tool_input_is_returned_to_the_model_not_crashing(fake_db):
    m = model(tool_call("calculate_solar_options", {"monthly_units": [0], "city": "x"}),
              AIMessage("Please tell me your monthly units."))
    out = run_agent({"session_id": "a" * 32}, [], "help", model=m)
    assert "units" in out["reply"]
    assert "error" in [x for x in m.seen[1] if isinstance(x, ToolMessage)][0].content


def test_agent_stops_if_it_loops_forever(fake_db):
    m = model(*[tool_call("get_price_list", {}, f"c{i}") for i in range(40)])
    out = run_agent({"session_id": "a" * 32}, [], "loop", model=m)
    assert "stuck" in out["reply"]


def test_appliance_tool_adds_up_watts_and_units():
    tool = {t.name: t for t in tools_module.make_tools({})}["estimate_appliance_load"]
    out = tool.invoke({"appliances": [{"name": "ceiling fan", "quantity": 3, "hours_per_day": 10},
                                      {"name": "LED light", "quantity": 5, "hours_per_day": 6},
                                      {"name": "fridge", "quantity": 1, "hours_per_day": 24}]})
    assert out["total_running_watts"] == 3 * 80 + 5 * 12 + 200
    assert out["units_per_day"] == round(3 * 80 * 10 / 1000 + 5 * 12 * 6 / 1000 + 200 * 24 * 0.45 / 1000, 1)


def test_save_contact_needs_consent_a_quote_and_a_real_number(fake_db):
    ctx = {"session_id": "a" * 32}
    tools = {t.name: t for t in tools_module.make_tools(ctx)}
    args = {"customer_name": "Ali Khan", "mobile_number": "0300-1234567", "preferred_option": "hybrid"}
    assert "error" in tools["save_contact"].invoke({**args, "customer_agreed": False})
    assert "error" in tools["save_contact"].invoke({**args, "customer_agreed": True})      # no quote yet
    tools["calculate_solar_options"].invoke({"monthly_units": [400], "city": "lahore"})
    assert "error" in tools["save_contact"].invoke({**args, "mobile_number": "12345", "customer_agreed": True})
    assert tools["save_contact"].invoke({**args, "customer_agreed": True})["saved"] is True
    insert = fake_db.ran("INSERT INTO Leads")[0][1]
    assert insert[3] == "03001234567" and insert[5] == "hybrid"


def test_bill_amount_tool_rejects_silly_amounts():
    tool = {t.name: t for t in tools_module.make_tools({})}["units_from_bill_amount"]
    assert "error" in tool.invoke({"bill_amount_rs": 5})
    assert tool.invoke({"bill_amount_rs": 25000})["estimated_monthly_units"] > 300
