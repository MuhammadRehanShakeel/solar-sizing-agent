"""
Test setup: the tests run WITHOUT SQL Server and WITHOUT any AI key.
  * pyodbc is replaced by a dummy, `fake_db` decides what each SQL query returns
  * ScriptedModel plays the language model: it returns the tool calls / answers we script,
    so the LangGraph loop, the tools and the routes are tested for real, for free and offline.
"""
import os
import sys
import types

os.environ.setdefault("DB_SERVER", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-hs256")
os.environ["GROQ_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["USE_NASA_SUNLIGHT"] = "0"          # tests never call NASA: they use the city table
sys.modules.setdefault("pyodbc", types.SimpleNamespace(connect=lambda *a, **k: None))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402
from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402


class FakeDB:
    """Answers SQL queries with rules: [(text_inside_query, answer_or_function)]."""

    def __init__(self):
        self.rules = []
        self.calls = []

    def on(self, fragment, answer):
        self.rules.insert(0, (fragment, answer))       # newest rule wins

    def __call__(self, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        self.calls.append((query, params))
        for fragment, answer in self.rules:
            if fragment in query:
                return answer(params) if callable(answer) else answer
        return [] if fetch_all else (None if fetch_one else True)

    def ran(self, fragment):
        return [c for c in self.calls if fragment in c[0]]


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    ids = iter(range(100, 10_000))
    import app.database

    def insert(q, p=None):
        db.calls.append((q, p))
        return next(ids)

    monkeypatch.setattr(app.database, "execute_query", db)
    monkeypatch.setattr(app.database, "execute_insert_and_get_id", insert)
    for name in list(sys.modules):
        module = sys.modules[name]
        if name.startswith("app.") and hasattr(module, "execute_query"):
            monkeypatch.setattr(module, "execute_query", db, raising=False)
        if name.startswith("app.") and hasattr(module, "execute_insert_and_get_id"):
            monkeypatch.setattr(module, "execute_insert_and_get_id", insert, raising=False)
    return db


class ScriptedModel(BaseChatModel):
    """A pretend LLM. `script` is a list of AIMessages returned one after another."""
    script: list = []
    seen: list = []

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        message = self.script.pop(0) if self.script else AIMessage("(no more script)")
        message.response_metadata = {"model_name": "scripted-test-model"}
        return ChatResult(generations=[ChatGeneration(message=message)])


def tool_call(name, args, call_id="call_1"):
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


@pytest.fixture
def scripted(monkeypatch):
    """Use: model = scripted([tool_call(...), AIMessage("answer")]) - every agent call uses this model."""
    def make(script):
        model = ScriptedModel(script=list(script), seen=[])
        import app.agent.llm as llm
        monkeypatch.setattr(llm, "chat_model", lambda tools: model)
        monkeypatch.setattr(llm, "available_models", lambda: ["scripted"])
        return model
    return make
