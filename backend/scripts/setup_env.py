"""
setup_env.py - Creates backend/.env the first time (with a strong random JWT_SECRET)
and asks for the free AI keys (typed hidden, saved only in backend/.env on this PC).

Run:  venv\\Scripts\\python.exe scripts\\setup_env.py [SQL_SERVER_NAME]
Existing values in .env are never overwritten.
"""
import getpass
import os
import secrets
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(BACKEND, ".env")
EXAMPLE = os.path.join(BACKEND, ".env.example")


def read(path):
    values = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                key, _, value = line.strip().partition("=")
                values[key] = value
    return values


def main():
    current = read(ENV)
    lines = open(EXAMPLE, encoding="utf-8").read().splitlines()
    defaults = {"JWT_SECRET": secrets.token_urlsafe(48)}
    if len(sys.argv) > 1 and sys.argv[1].strip():
        defaults["DB_SERVER"] = sys.argv[1].strip()
    for key, where in (("GROQ_API_KEY", "https://console.groq.com/keys"),
                       ("GEMINI_API_KEY", "https://aistudio.google.com/apikey")):
        if not current.get(key) and sys.stdin.isatty():
            value = getpass.getpass(f"Paste your {key} from {where} (hidden; Enter = skip): ").strip()
            if value:
                defaults[key] = value
    out = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            value = current.get(key) or defaults.get(key) or value
            out.append(f"{key}={value}")
        else:
            out.append(line)
    with open(ENV, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("[OK] backend/.env is ready (JWT_SECRET is random; keys stay on this PC)")


if __name__ == "__main__":
    main()
