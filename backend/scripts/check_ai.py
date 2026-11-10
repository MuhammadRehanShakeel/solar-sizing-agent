"""
check_ai.py - Tests your AI keys and shows which models they can use.

Run:  venv\\Scripts\\python.exe scripts\\check_ai.py
If a model in .env has been retired, pick another one from the list it prints.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config  # noqa: E402


def check_groq():
    if not config.GROQ_API_KEY:
        print("[--] GROQ_API_KEY is empty (chat will use Gemini; voice is off)")
        return
    from groq import Groq
    client = Groq(api_key=config.GROQ_API_KEY)
    names = sorted(m.id for m in client.models.list().data)
    print("[OK] Groq key works. Models:", ", ".join(names))
    if config.GROQ_MODEL not in names:
        print(f"[!] GROQ_MODEL={config.GROQ_MODEL} is not in the list - change it in backend/.env")
    reply = client.chat.completions.create(model=config.GROQ_MODEL, max_tokens=20,
                                           messages=[{"role": "user", "content": "Say: solar ready"}])
    print("     test answer:", reply.choices[0].message.content)


def check_gemini():
    if not config.GEMINI_API_KEY:
        print("[--] GEMINI_API_KEY is empty (bill photos are off)")
        return
    from google import genai
    from app.services import gemini
    client = gemini.make_client()
    names = sorted(m.name.replace("models/", "") for m in client.models.list() if "flash" in m.name)
    print("[OK] Gemini key works. Flash models:", ", ".join(names))
    from app.services import gemini
    chosen = gemini.working_model(client)
    print(f"[OK] Gemini model in use: {chosen}")
    if chosen != config.GEMINI_MODEL:
        print(f"     (GEMINI_MODEL={config.GEMINI_MODEL} in backend/.env is retired - you can change it to {chosen})")
    reply = client.models.generate_content(model=chosen, contents="Say: solar ready")
    print("     test answer:", (reply.text or "").strip())


if __name__ == "__main__":
    for check in (check_groq, check_gemini):
        try:
            check()
        except Exception as e:
            print(f"[ERROR] {check.__name__}: {e}")
