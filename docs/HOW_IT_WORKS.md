# How SolarSaathi works

SolarSaathi is an **AI agent** that does a solar salesperson's first job: it learns about the home,
works out the right system and makes a quotation. It's an "agent" and not just a chatbot because it
**decides by itself which tools to use** (bill reader, bill estimator, appliance calculator,
sizing calculator, lead saver), uses their results, and keeps going until the job is done.

## 1. The big picture

```
 Customer (web / Android / voice)
        │  text, voice clip or bill photo
        ▼
 React app ──/api──► FastAPI backend
                        │
          ┌─────────────┼────────────────────────────┐
          ▼             ▼                            ▼
   Whisper (Groq)   Gemini vision             LangGraph agent
   voice → text     bill photo → JSON     ┌── LLM (Groq, Gemini as backup)
                                          │      │ "I need a tool"
                                          │      ▼
                                          └── tools.py ──► sizing.py / tariff.py (plain Python maths)
                                                         └► SQL Server (quotes, leads, prices)
                        │
                        ▼
              answer + quotation (cards, charts, PDF, share link)
                        │
                        ▼
 Installer staff: dashboard, leads, conversations, price list
```

## 2. The agent (`backend/app/agent/`)

`graph.py` builds a small **LangGraph** state machine:

```
START → agent ──(asks for a tool)──► tools ──(result)──► agent → … → END
            └──(plain answer)───────────────────────────────────► END
```

* **agent node**: the language model reads the system prompt, the chat so far and any tool results.
  It either answers or returns a *tool call* (a function name plus JSON arguments).
* **tools node**: LangGraph's `ToolNode` runs the Python function and adds the result to the chat.
* The loop stops when the model answers in plain text, or after `MAX_AGENT_STEPS` rounds
  (so a confused model can never loop forever and burn the free quota).

### The tools (`tools.py`)

| Tool | What it does |
|---|---|
| `units_from_bill_amount` | "My bill is Rs 25,000": finds the units that give that bill under the NEPRA tariff |
| `estimate_current_bill` | units → bill, with the breakdown (energy, fixed charges, FC surcharge, duty, GST) |
| `estimate_appliance_load` | "3 fans, 5 lights, fridge" → running watts (battery size) and units per month |
| `calculate_solar_options` | the main tool: on-grid, hybrid and off-grid sizes, costs, savings, payback; **saves the quotation** |
| `get_price_list` | the installer's current prices |
| `save_contact` | name + mobile for a call-back, **only with consent**, with a validated Pakistani number |

Every tool **checks its inputs**, because the model can make mistakes (for example 0 units or a fake
phone number). A bad input returns `{"error": ...}` to the model, which then asks the customer again.

### Why the AI never does the maths

Language models are bad at arithmetic and sometimes invent numbers. A sales agent that invents a price is
dangerous. So:

1. All numbers come from `sizing.py` / `tariff.py`: plain, tested Python that gives the same answer every time.
2. The system prompt says: *every number you say must come from a tool result*.
3. `evaluation/eval_agent.py` checks this: it compares every number in the agent's answers with
   the numbers in the tool results and the customer's messages.

### Memory

The chat is saved in SQL Server (`ChatMessages`). On every message the agent gets the last 16 messages,
plus a short summary of the latest quotation and the bill numbers, in the system prompt. So it remembers
the conversation without sending huge histories (saving tokens on the free tier).

### Two free models with automatic backup (`llm.py`)

`ChatGroq(...).bind_tools(tools).with_fallbacks([ChatGoogleGenerativeAI(...).bind_tools(tools)])`.
If Groq is busy (free-tier limit) or down, LangChain silently asks Gemini instead. The model that answered
is saved with each message, so staff can see it.

## 3. The calculator (`services/sizing.py`, `services/tariff.py`)

1. **Usage**: 12 months from the bill (or one average repeated).
2. **Panels**: size so the panels make about what the house uses in a year:
   `kW = yearly units ÷ city yield`. The city yield (units per kW per year, after losses) is
   1,450 for Islamabad/Lahore, up to 1,750 for Quetta. Since net billing (Feb 2026) an exported unit earns
   only about Rs 11 while an imported unit costs Rs 22–47, so making much more than you use rarely pays.
3. **Inverter**: the next market size where panels ≤ 1.2 × inverter.
4. **Battery** (hybrid): backup load × load-shedding hours ÷ 90 % usable ÷ 92 % efficiency, rounded up
   to 5 kWh packs. Off-grid: the night-time use plus 20 %, and 50 % more panels for winter fog.
5. **Month-by-month simulation**: solar per month (with a seasonal factor), how much is used directly
   (daytime share ~45 %), how much the battery shifts to the night, how much is exported and imported.
6. **Bills**: the NEPRA domestic tariff (Feb 2026): non-protected slabs where one rate applies to every
   unit, fixed charges per kW, FC surcharge, 1.5 % electricity duty, 18 % GST, PTV fee.
   With solar: `bill(imported units) − exported units × export rate`, but fixed charges are always paid.
7. **Saving, payback, 25-year saving** (0.5 % panel ageing per year) and CO₂ (0.45 kg per grid unit).
8. **Recommendation** with a reason: no grid → off-grid; 2+ hours of load-shedding → hybrid; otherwise on-grid.
   Notes for small roofs, a budget limit or a sanctioned load that's too small.

Prices come from the `Prices` table, so the installer changes them on the Prices page without coding.

## 4. Bill photos (`services/bill_reader.py`)

Gemini (multimodal) gets the photo and a **response schema** (Pydantic), so it must answer in a fixed JSON
shape: DISCO, tariff, sanctioned load, units of the bill month and the 12-month history table.
Python then throws away impossible values (a misread "4100" for "410" would make a 30 kW system).
**Privacy:** the name, address and reference number are not requested, and the photo is not saved.

## 5. Voice (`services/voice.py`, `VoiceButton.jsx`, `speech.js`)

* **Speech to text**: the browser records a clip (`MediaRecorder`), the backend sends it to Whisper
  (`whisper-large-v3-turbo` on Groq, free). Whisper understands English, Urdu and mixed speech. The text
  is shown to the customer and sent like a typed message.
* **Text to speech**: the browser's built-in `speechSynthesis` reads the answer aloud (free, offline).
  An Urdu voice is used for Urdu script if the phone has one.
* Phone browsers only allow the microphone on **https** pages, so `start_phone.bat` serves the app over https.

## 6. Quotations

Every calculation is saved in `Quotes` with a random 32-character `public_token`. The link
`/quote/<token>` shows it to anyone who has the link (like an unlisted video); there's no list of quotes
for strangers. The PDF (`quote_pdf.py`, ReportLab) has the three options, the price breakdown, a usage
vs solar chart and all assumptions.

## 7. The installer side

* **Dashboard**: conversations, quotations, leads, value quoted, recommended systems, cities, and
  which model answered.
* **Leads**: call / WhatsApp buttons, status pipeline (new → contacted → site visit → won / lost), notes.
* **Conversations**: read any chat, with the tools the agent used for each answer.
* **Prices** (admin), **Staff accounts** (admin), **Audit log** (admin).

## 8. Security

| Risk | What stops it |
|---|---|
| Someone reads other customers' chats | 32-character random session ids and quote tokens; staff pages need a login |
| Prompt injection ("ignore your rules…") | the system prompt treats customer text and bill data as information, never instructions. The tools validate everything; prices only change on the admin page |
| Using the agent as a free general chatbot | topic rule in the prompt, 1,000 characters per message, 40 messages per chat, rate limits per IP |
| Fake uploads | bill photos: type and magic bytes checked, 6 MB max; audio 3 MB max |
| Password guessing | bcrypt, lockout after 5 wrong passwords, same error message for unknown emails |
| Stolen / old tokens | role and active status re-checked on every request; `token_version` ends old sessions |
| SQL injection | every query uses `?` parameters |
| Secrets on GitHub | keys only in `backend/.env` (git-ignored), gitleaks in CI |

## 9. Tests

`backend/tests` runs with **no SQL Server and no AI key**: a fake database and a *scripted model* that returns the
tool calls we choose. So the real LangGraph loop, the tools, the routes and the security rules are tested
on every push for free. `evaluation/eval_agent.py` tests the real models separately.

## 10. Version 2: what a real customer asks

**Load-shedding the way people say it (`sizing.outage_profile`).** "Roz 2 ghante", "hafte mein ek dafa
9 se 2" and "raat 10 se 12" all become the same thing: days per week + start and end time. The day is
split into sunshine (8 am - 5 pm) and dark hours. This matters because:
* an **on-grid** inverter must switch off when WAPDA is off (so line workers are safe), so the sunshine
  during a daytime cut is lost - the simulation removes it;
* a **hybrid** runs the house straight from the panels in a daytime cut, so it needs only a small battery;
  a night cut needs battery energy = backup load x dark hours.
A hybrid is recommended when cuts add up to 7+ hours a week, or 2+ dark hours on 3+ days.

**Every WAPDA choice (`_simulate`, `_scenarios`).** For each system and each month we know what the
panels make, what is used directly, what goes through the battery, what is still needed from WAPDA and
what is left over. From that, four bills: net billing (left-over sold at ~Rs 11), connected without a
green meter (left-over wasted), off-grid disconnected (Rs 0) and off-grid with WAPDA as backup only.
Off-grid panels are sized for the worst (winter) month, and months where the sun may fall short are listed.

**NASA sunlight (`services/sunlight.py`).** NASA POWER gives 20+ years of average daily sunlight for any
point. Output per kW = sunlight x days x tilt gain (south-facing panels catch more winter sun) x 0.78
(heat, dust, wiring and inverter losses). For Islamabad this gives about 1,490 units per kW a year,
close to measured systems. Answers are cached; with no internet the city table is used and the quote says so.

**Packages and instalments.** Economy and Premium are a % of the Standard parts price (set on the Prices
page). Instalments use the normal loan formula: P x r / (1 - (1 + r)^-n).

**Bill check.** The bill photo result is shown to the customer first; the agent only continues after
"These are right" (or their corrections). The AI never silently uses a misread number.

**Gemini that keeps working (`services/gemini.py`).** Google retires model names and free models get
overloaded. Each call tries the last model that worked, then the next free Flash model; retired names are
remembered, a wrong key is still reported.

## Sources for the numbers (October 2026)

* Sunlight: NASA POWER climatology API, parameter ALLSKY_SFC_SW_DWN (https://power.larc.nasa.gov)

* NEPRA domestic tariff S.R.O. 279(I)/2026 and net billing S.R.O. 251(I)/2026: summarised by
  [toolsfluent.com](https://www.toolsfluent.com/blog/electricity-slab-rates-pakistan-2026) and
  [toolsfluent net metering guide](https://www.toolsfluent.com/blog/net-metering-pakistan-complete-guide)
* Panel prices Rs 40–46/W (N-type, Tier-1, July–Aug 2026):
  [toolsfluent panel prices](https://www.toolsfluent.com/blog/solar-panel-price-pakistan-2026)
* System and battery prices: [on-grid vs hybrid 2026](https://www.toolsfluent.com/blog/on-grid-vs-hybrid-solar-pakistan-2026)

Prices move every month: the installer updates them on the Prices page.
