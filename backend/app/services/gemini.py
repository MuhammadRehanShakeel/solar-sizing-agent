"""
gemini.py - Uses whichever free Gemini model is working right now.

Two real problems with the free Gemini API:
  1. names get retired ("gemini-2.5-flash is no longer available to new users")  -> 404
  2. a model can be overloaded for a while ("high demand", timeouts)            -> 503 / 504 / 429
So we keep a short list of free Flash models. A call tries the last model that worked first, then the
others. Retired names are remembered and never tried again; busy ones are simply skipped this time.
A wrong key (401/403) is NOT hidden - it is reported as it is.
"""
import logging
import threading

from app import config

log = logging.getLogger("gemini")
CANDIDATES = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
_chosen = None                 # last model that answered
_missing = set()               # retired names: never try again
_lock = threading.Lock()
_warming = False


def make_client():
    """A Gemini client that gives up quickly (30 s, no hidden retries) so we can switch model at once."""
    from google import genai
    from google.genai import types
    return genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(
        timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1)))


def candidates() -> list:
    names = [_chosen, config.GEMINI_MODEL] + CANDIDATES
    return [n for n in dict.fromkeys(names) if n and n not in _missing]      # keep order, no repeats


def is_missing_model(error: Exception) -> bool:
    text = str(error)
    return "404" in text or "NOT_FOUND" in text or "no longer available" in text


def is_busy(error: Exception) -> bool:
    text = str(error).lower()
    return any(k in text for k in ("503", "504", "429", "unavailable", "resource_exhausted", "deadline",
                                   "high demand", "overloaded", "timed out", "timeout"))


def generate_with_backups(client=None, **kwargs):
    """client.models.generate_content(...) on the first model that answers."""
    global _chosen
    client = client or make_client()
    last = None
    for name in candidates():
        try:
            response = client.models.generate_content(model=name, **kwargs)
        except Exception as e:
            if is_missing_model(e):
                _missing.add(name)
                log.warning("Gemini model %s is retired for this key - skipping it from now on", name)
            elif is_busy(e):
                log.warning("Gemini model %s is busy right now (%s) - trying the next one", name, str(e)[:60])
            else:
                raise                                   # e.g. wrong key: tell the truth
            last = e
            continue
        if name != _chosen:
            log.info("Gemini model in use: %s", name)
            _chosen = name
        return response
    raise last or RuntimeError("No Gemini model is configured")


def working_model(client=None) -> str:
    """Name of a model that answers right now (a 5-token test call)."""
    from google.genai import types
    with _lock:
        if _chosen:
            return _chosen
        generate_with_backups(client, contents="ok", config=types.GenerateContentConfig(max_output_tokens=5))
        return _chosen


def chat_model_name() -> str:
    """For the LangChain backup chat model: no network call, just the best guess."""
    names = candidates()
    return names[0] if names else None


def warm_up_in_background():
    """At server start: find a working model so the first bill photo is fast. Runs only once at a time."""
    global _warming
    if not config.GEMINI_API_KEY or _chosen or _warming:
        return
    _warming = True

    def run():
        global _warming
        try:
            log.info("Gemini model ready: %s", working_model())
        except Exception as e:
            log.warning("Gemini is not available right now (bill photos may be slow): %s", str(e)[:150])
        finally:
            _warming = False

    threading.Thread(target=run, name="gemini-warm-up", daemon=True).start()


def forget():
    """Tests / manual reset."""
    global _chosen
    _chosen = None
    _missing.clear()
