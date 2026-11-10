# Interview notes: SolarSaathi

## 30-second pitch

"SolarSaathi is an AI agent for solar installers in Pakistan. A home owner uploads a photo of their
electricity bill, or just talks to it by voice in Urdu or English. The agent reads the bill, asks about
load-shedding and what must keep running, then calls a sizing tool and gives three options (on-grid, hybrid,
off-grid) with price, monthly saving and payback, plus a PDF quotation. If the customer agrees, it saves a
lead for the sales team. I built it with LangGraph and free models (Groq with Gemini as an automatic backup),
FastAPI, SQL Server and React, and it also runs as an Android app."

## Likely questions

**What makes it an agent and not a chatbot?**
It chooses actions. The model decides which tool to call and with what arguments (read a bill amount,
estimate appliances, calculate, save a contact), sees the result, and decides the next step. LangGraph runs that
loop: agent node → tools node → agent node, until it answers.

**Why LangGraph instead of a plain LangChain chain?**
The flow is a loop with a decision in it, not a straight line. LangGraph makes the loop explicit (nodes and
edges), gives a step limit (`recursion_limit`) so it can't loop forever, and it's easy to add nodes later,
e.g. a human-approval step before sending a quote.

**How do you stop the AI from inventing prices?**
Three layers: (1) all maths is in plain Python tools (`sizing.py`, `tariff.py`) with unit tests; (2) the prompt
says every number must come from a tool result; (3) an evaluation script checks every number in the answers
against the tool outputs and the customer's own words.

**Why two models?**
Free tiers have rate limits. `with_fallbacks()` makes Gemini answer when Groq is busy, so the customer never sees
an error. Each saved message records which model answered, so I can monitor it on the dashboard.

**How does the bill reading work?**
Gemini is multimodal. I send the photo with a Pydantic response schema, so the answer is always the same JSON
shape. Then Python validates the numbers (a misread digit must not create a 30 kW system). I don't ask for the
name, address or reference number, and the photo isn't stored: privacy by design.

**How does voice work?**
The browser records with MediaRecorder; the backend sends the clip to Whisper (large-v3-turbo on Groq), which handles
Urdu/English code-switching. The answer is read aloud by the browser's speechSynthesis, so it costs nothing.
Phones need https for the mic, which is why there is a phone-mode script.

**How did you size the system?**
Annual usage ÷ city specific yield (kWh/kWp/yr after losses), rounded to whole panels; inverter by DC/AC ratio
≤ 1.2; battery from backup load × outage hours ÷ depth of discharge ÷ efficiency, rounded to packs. Then a
month-by-month simulation of self-use, battery shifting, export and import, priced with the 2026 NEPRA tariff and
net billing. Payback = cost ÷ yearly saving.

**What changed with net billing and why does it matter?**
Since February 2026 new solar users get about Rs 11 for an exported unit while buying costs Rs 22–47. So
oversizing is a bad deal, and using your own power (or a battery) is worth more. That is built into the
simulation and the agent's advice.

**How do you test something that uses an LLM?**
Two levels. Unit/integration tests use a *scripted model* (a fake chat model returning the tool calls I choose),
so the real graph, tools, database calls and API are tested offline and free in CI. Then `eval_agent.py`
runs 10 scripted customers against the real models and scores tool use, the right recommendation,
made-up numbers, guard rails, language and speed.

**Security?**
Customers don't log in, but chats and quotes use random 32-character ids. Staff use bcrypt passwords, lockout and
role checks on every request. Rate limits and message/turn limits protect the free quota. Uploads are checked by
magic bytes. All SQL is parameterised. Keys live only in `.env`, and gitleaks scans every push.

**What would you add next?**
WhatsApp Business integration (most Pakistani customers prefer it), satellite roof measurement, real-time
panel prices from distributors, Urdu text-to-speech on the server, and a human-approval step before a quote
goes out.

**"A customer said the light goes once a week from 9 to 2. How does your system handle that?"**
The agent turns any wording into days per week + start/end time and passes it to the calculator.
The calculator splits the cut into sunshine and dark hours: an on-grid system loses the sunshine during
the cut (it must switch off by law), a hybrid runs from the panels, and only dark hours need battery.
For one daytime cut a week it recommends on-grid and explains what the hybrid would add.

**"How do you know the solar output is right?"**
NASA POWER satellite data for the exact location, converted with a tilt gain and a 0.78 performance
ratio; for Islamabad that is ~1,490 units per kW a year, in line with real systems (1,450-1,550).

**"What if the AI misreads the bill?"**
The customer sees the 12 months it read and can fix them before anything is calculated. The AI
cannot use bill numbers that were not confirmed.

**"What if Gemini is down?"**
Chat: Groq first, Gemini as LangChain fallback. Bill reading: the code rotates through free Gemini
models, skipping busy (503/504/429) and retired (404) ones; a wrong key is still shown as an error.

## Numbers to remember

* 3 options per quote, 6 tools, 2 free models with automatic backup, voice in Urdu + English
* NEPRA 2026 tariff + net billing at ~Rs 11/unit export
* automated tests run with no database and no API key (see README for the count)
* agent evaluation: see `evaluation/RESULTS.md`
