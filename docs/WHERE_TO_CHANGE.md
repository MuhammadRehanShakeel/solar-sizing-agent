# Where to change things

| I want to… | Change | File |
|---|---|---|
| Change panel / inverter / battery prices | the Prices page (admin), no code | `/staff/prices` |
| Change default prices for a new database | `DEFAULT_PRICES` | `backend/app/services/prices.py` |
| Update the electricity tariff (new NEPRA schedule) | `NON_PROTECTED`, `PROTECTED`, `FIXED_*`, `FC_SURCHARGE` | `backend/app/services/tariff.py` |
| Change the net-billing export rate | Prices page → "Net-billing export rate" | `/staff/prices` |
| Add a city | `CITIES` (name, latitude, longitude, fallback yield) | `backend/app/services/sunlight.py` |
| Change the solar output maths (tilt, losses) | `TILT_GAIN`, `PERFORMANCE_RATIO` | `backend/app/services/sunlight.py` |
| Switch NASA sunlight off (no internet) | `USE_NASA_SUNLIGHT=0` | `backend/.env` |
| Change when load-shedding needs a hybrid | `weekly >= 7 or dark_hours >= 2` in the "Recommend one" block | `backend/app/services/sizing.py` |
| Change daylight hours (sun 8 am - 5 pm) | `DAYLIGHT_HOURS`, `SUN_HOURS` | `config.py`, `sizing.py` |
| Change package prices / parts | Prices page (Economy / Premium %) and `TIERS` | `/staff/prices`, `sizing.py` |
| Change instalment markup / down payment | Prices page → Financing | `/staff/prices` |
| Add an appliance to the backup planner | `CATALOGUE` | `backend/app/services/appliances.py` |
| Change survey time slots / rules | `SLOTS`, `check()` | `backend/app/services/booking.py` |
| Translate more of the website | `TEXT` (English, Urdu) | `frontend/src/services/i18n.jsx` |
| Change how big the system is sized | `target_kw` in `calculate_options()` | `backend/app/services/sizing.py` |
| Change when hybrid is recommended | the "Recommend one option" block | `sizing.py` |
| Change the agent's tone, questions or rules | `SYSTEM_PROMPT` | `backend/app/agent/prompts.py` |
| Give the agent a new skill | add a `@tool` function in `make_tools()` (+ a test) | `backend/app/agent/tools.py` |
| Change which Gemini models are tried | `CANDIDATES` | `backend/app/services/gemini.py` |
| Add an appliance wattage | `APPLIANCE_WATTS` | `tools.py` |
| Use a different AI model | `GROQ_MODEL` / `GEMINI_MODEL` | `backend/.env` |
| See which models my keys can use | `scripts\windows\check_ai_keys.bat` | |
| Change chat limits (length, turns, steps) | `MAX_MESSAGE_CHARS`, `MAX_TURNS_PER_SESSION`, `MAX_AGENT_STEPS` | `backend/app/config.py` |
| Change what is read from a bill photo | `BillData` + `PROMPT` | `backend/app/services/bill_reader.py` |
| Change the installer name / phone on quotes | `INSTALLER_NAME`, `INSTALLER_PHONE` | `backend/.env` |
| Change the PDF quotation | `make_quote_pdf()` | `backend/app/services/quote_pdf.py` |
| Change the welcome message or suggestion chips | `WELCOME`, `SUGGESTIONS` | `frontend/src/pages/Chat.jsx` |
| Change colours / fonts | `colors`, `theme` | `frontend/src/theme.js` |
| Change the voice (speed, language) | `speak()` | `frontend/src/services/speech.js` |
| Change ports | `API_PORT` in `.env` + `vite.config.js` | both |
| Use the Android app | set `VITE_API_URL=http://<PC-IP>:5002` in `frontend/.env`, `API_HOST=0.0.0.0` in `backend/.env`, then `npm run android:sync` | |

After any backend change, run `scripts\windows\run_tests.bat`. All tests must pass.
After changing the prompt or the model, run `scripts\windows\run_agent_eval.bat` and compare the scores.
