"""Gemini model names get retired and models get busy; the app must move on by itself."""
from app.services import gemini


class FakeModels:
    def __init__(self, behaviour):
        self.behaviour, self.tried = behaviour, []           # name -> "ok" | "404" | "503" | "504" | "401"

    def generate_content(self, model, contents, config=None):
        self.tried.append(model)
        result = self.behaviour.get(model, "404")
        if result == "ok":
            return f"answer from {model}"
        messages = {"404": "404 NOT_FOUND. This model is no longer available to new users.",
                    "503": "503 UNAVAILABLE. This model is currently experiencing high demand.",
                    "504": "504 DEADLINE_EXCEEDED. Deadline expired before operation could complete.",
                    "401": "401 API key not valid"}
        raise RuntimeError(messages[result])


class FakeClient:
    def __init__(self, behaviour):
        self.models = FakeModels(behaviour)


def setup_function():
    gemini.forget()


def teardown_function():
    gemini.forget()


def test_retired_and_busy_models_are_skipped(monkeypatch):
    monkeypatch.setattr(gemini.config, "GEMINI_MODEL", "gemini-2.5-flash")
    client = FakeClient({"gemini-2.5-flash": "404", "gemini-3.8-flash": "503", "gemini-3.6-flash": "ok"})
    assert gemini.generate_with_backups(client, contents="bill") == "answer from gemini-3.6-flash"
    assert client.models.tried == ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.6-flash"]
    # next call: the working model first, the retired one never again
    client.models.tried.clear()
    gemini.generate_with_backups(client, contents="bill")
    assert client.models.tried == ["gemini-3.6-flash"]


def test_timeout_moves_on(monkeypatch):
    monkeypatch.setattr(gemini.config, "GEMINI_MODEL", "gemini-3.8-flash")
    client = FakeClient({"gemini-3.8-flash": "504", "gemini-3.6-flash": "ok"})
    assert gemini.working_model(client) == "gemini-3.6-flash"


def test_wrong_key_is_not_hidden(monkeypatch):
    monkeypatch.setattr(gemini.config, "GEMINI_MODEL", "gemini-3.8-flash")
    client = FakeClient({"gemini-3.8-flash": "401"})
    try:
        gemini.generate_with_backups(client, contents="x")
        assert False, "should raise"
    except RuntimeError as e:
        assert "401" in str(e)
    assert client.models.tried == ["gemini-3.8-flash"]


def test_all_busy_raises_busy_error(monkeypatch):
    monkeypatch.setattr(gemini.config, "GEMINI_MODEL", "gemini-3.8-flash")
    client = FakeClient({n: "503" for n in gemini.CANDIDATES})
    try:
        gemini.generate_with_backups(client, contents="x")
        assert False
    except RuntimeError as e:
        assert gemini.is_busy(e)
