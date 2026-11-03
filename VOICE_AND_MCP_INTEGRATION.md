# Voice & MCP Integration

This document explains what was built on the `ft/voice-integration` branch: giving the itinerary agent real-world tools through the **Model Context Protocol (MCP)**, and letting users create trips and listen to itineraries by **voice**. It covers what each piece does, why it was built that way, and how the pieces fit together.

---

## 1. Why MCP?

Before this work, the itinerary agent only had one tool: `search_travel_knowledge`, which queries a local curated knowledge base. That's fine for general tips, but it can't tell you *today's* weather in Lisbon, or *real* restaurant names near a hotel, or *actual* driving distances. The agent needed live, real-world data.

**MCP (Model Context Protocol)** is a standard way to expose tools to an LLM agent as a separate server process, communicating over a defined protocol (stdio, in our case) instead of importing tool code directly into the agent process. We used it here because:

- It decouples "what tools exist" from "how the agent loads them" — tools can be added, swapped, or even run on a different machine without touching the agent's code.
- `langchain-mcp-adapters` turns any MCP server's tools into LangChain-compatible tools automatically, so no manual wrapping is needed.
- It mirrors how production agent systems are typically composed: native, in-process tools for app-specific logic (like the knowledge base) alongside MCP tools for shared/external capabilities.

---

## 2. Building the MCP server

**File:** [`app/mcp_servers/travel_tools_server.py`](app/mcp_servers/travel_tools_server.py)

This is a standalone script that exposes three tools using `FastMCP`:

| Tool | What it does | External API used |
|---|---|---|
| `get_weather` | Current weather/forecast for a destination, to decide indoor vs. outdoor activities | Open-Meteo |
| `find_places` | Real, named points of interest (restaurants, museums, attractions, etc.) near a destination | Overpass API (OpenStreetMap data) |
| `get_route` | Distance and driving time between two locations | OSRM |

Each tool is a plain Python function decorated with `@mcp.tool()`:

```python
@mcp.tool()
def get_weather(destination: str) -> str:
    """ Get the weather and forecast for a destination city... """
    ...
```

FastMCP reads the function signature and docstring to automatically generate the tool's schema (name, parameters, description) that the LLM will see — no separate schema definitions needed.

**Why these specific tools:** each one answers a question the agent's system prompt explicitly asks it to verify — realistic weather-appropriate plans, real (non-hallucinated) place names, and geographically sane routing between activities.

**Why a bare `try/except` returning a string:** if a tool throws, we don't want it to crash the agent's tool-calling loop — we want the LLM to see a plain-English failure message (e.g. `"Failed to fetch places for Paris"`) and route around it, the same way a human assistant would say "I couldn't find that" and move on.

At the bottom, the server is run directly over stdio:
```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```
This means the server isn't a long-running network service — it's launched as a subprocess per app lifecycle, and communicates with its parent process via stdin/stdout.

---

## 3. Building the MCP client

**File:** [`app/agent/mcp_client.py`](app/agent/mcp_client.py)

```python
mcp_client = MultiServerMCPClient({
    "travel_tools": {
        "command": "python",
        "args": [str(TRAVEL_SERVER_PATH)],
        "transport": "stdio",
    }
})

async def load_mcp_tools():
    return await mcp_client.get_tools()
```

`MultiServerMCPClient` (from `langchain-mcp-adapters`) is configured to spawn `travel_tools_server.py` as a subprocess and talk to it over stdio. `load_mcp_tools()` is the single entry point the rest of the app uses to fetch the MCP tools as ready-to-use LangChain `Tool` objects.

**Why `MultiServerMCPClient` even though we only have one server:** it's the standard adapter class regardless of server count, and naming the server (`"travel_tools"`) keeps the door open to add more MCP servers later (e.g. a flights server, a currency server) without changing how the agent consumes tools.

**Why this had to be async:** spawning a subprocess and listing its tools over stdio is inherently an I/O operation — `get_tools()` is a coroutine, so loading tools can't happen at plain import time; it has to happen inside an event loop.

---

## 4. Rewiring the agent graph for async tools

**File:** [`app/agent/graph.py`](app/agent/graph.py)

Before MCP, tools were all synchronous Python functions and the graph could be built once, up front. MCP tools changed that in two ways:

### 4a. Merging native + MCP tools

```python
async def build_itinerary_graph():
    mcp_tools = await load_mcp_tools()
    runtime_tools = [*NATIVE_TOOLS, *mcp_tools]
    all_tools = [*runtime_tools, save_itinerary_tool]
    model_with_tools = llm.bind_tools(all_tools, tool_choice="any")
    ...
```

`NATIVE_TOOLS` (currently just `search_travel_knowledge`, defined in [`app/agent/tools.py`](app/agent/tools.py)) are in-process LangChain tools. `mcp_tools` are the same `Tool` interface, just backed by the MCP subprocess. Because `langchain-mcp-adapters` normalizes MCP tools to the standard LangChain `Tool` type, the agent and the `ToolNode` don't need to know or care which tools are native vs. MCP — they're used identically in `bind_tools()` and in the `ToolNode(runtime_tools)` graph node.

`save_itinerary_tool` is kept separate from `runtime_tools` and only added to the LLM's tool list (`all_tools`), not to the `ToolNode` — because it isn't actually "run"; it's a structured-output signal the `finalize` node reads directly off the tool call (see `route_after_agent` / `finalize` below).

### 4b. Building the graph once at startup, not per request

Originally, building the graph meant spawning the MCP subprocess every time — expensive and unnecessary. Instead:

```python
_itinerary_graph = None

async def init_itinerary_graph():
    global _itinerary_graph
    _itinerary_graph = await build_itinerary_graph()

def get_itinerary_graph():
    if _itinerary_graph is None:
        raise RuntimeError("Itinerary graph has not been initialised yet.")
    return _itinerary_graph
```

`init_itinerary_graph()` is called once, from the FastAPI lifespan (see below). `get_itinerary_graph()` is a plain synchronous getter that every request uses to grab the already-built graph — one MCP subprocess for the life of the app, not one per request.

### 4c. Routing and finalizing

```python
def route_after_agent(state: ItineraryAgentState) -> str:
    ...
    for call in tool_calls:
        if call["name"] == "save_itinerary":
            return "finalize"
    return "tools"
```

The agent loop is: call the LLM → if it wants to call `save_itinerary`, go straight to `finalize` and extract the structured itinerary from the tool call's arguments; otherwise, route to the `tools` node (which executes whichever real tool — native or MCP — the LLM asked for) and loop back to the agent.

---

## 5. Wiring the graph into the FastAPI app

**File:** [`app/main.py`](app/main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_itinerary_graph()
    yield

app = FastAPI(title="AI_Vacation_Planner", lifespan=lifespan)
```

The graph (and its MCP subprocess) is built exactly once, when the FastAPI app starts up, and torn down implicitly when the app stops.

**File:** [`app/services/llm_service.py`](app/services/llm_service.py)

```python
async def generate_itinerary_json(trip: models.Trip) -> dict:
    initial_state = {...}
    itinerary_graph = get_itinerary_graph()
    result = await itinerary_graph.ainvoke(initial_state)
    ...
```

### Why `ainvoke` instead of `invoke`

This was a real bug caught during testing. Since the graph's tool node can execute MCP tools (coroutines), calling it with the synchronous `graph.invoke(...)` failed with:

```
NotImplementedError: StructuredTool does not support sync invocation.
```

The fix: `generate_itinerary_json` became `async def` and switched to `await itinerary_graph.ainvoke(...)`. That required propagating `async`/`await` one level up, into the router:

**File:** [`app/routers/itineraries.py`](app/routers/itineraries.py)

```python
@router.post("/", ...)
async def create_itinerary(request: models.ItineraryGenerateRequest, ...):
    ...
    llm_response_dict = await llm_service.generate_itinerary_json(trip)
    ...
```

**Known trade-off:** the DB calls inside this route (`trip_service.get_trip_by_id`, `itinerary_service.create_itinerary`, etc.) are still synchronous SQLModel calls. Inside an `async def` route, synchronous blocking calls run directly on the event loop rather than in a thread pool, so under concurrent load they could block other requests. This wasn't a problem for manual testing (one request at a time) but would be worth addressing (async SQLModel sessions, or `run_in_threadpool`) before scaling to concurrent traffic.

---

## 6. Why voice integration?

The goal: let a user describe a trip out loud instead of filling a form, and let them *listen* to their itinerary instead of only reading it — useful hands-free (e.g. while driving or packing) and more natural for quickly capturing trip ideas.

---

## 7. Voice input: audio → structured trip

**File:** [`app/services/voice_service.py`](app/services/voice_service.py)

```python
def transcribe_and_extract_trip(audio_bytes: bytes, mime_type: str) -> models.TripCreate:
    if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise ValueError(f"Unsupported audio format: {mime_type}")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("Audio file is too large; please send a shorter clip.")
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    message = HumanMessage(content=[
        {"type": "text", "text": EXTRACTION_PROMPT},
        {"type": "media", "data": encoded_audio, "mime_type": mime_type}
    ])
    llm = ChatGoogleGenerativeAI(model=settings.voice_llm_model, api_key=settings.google_api_key) \
        .with_structured_output(models.TripCreate)
    return llm.invoke([message])
```

**How it works:** rather than running a separate speech-to-text step and then a separate text-extraction step, the raw audio bytes are sent *directly* to a multimodal Gemini model as a `media` content block, alongside a prompt instructing it to extract trip details (`destination`, `days`, `budget`, `trip_style`) with sensible defaults when something isn't mentioned. `.with_structured_output(models.TripCreate)` forces the model's response to conform exactly to the `TripCreate` schema — so the output can be passed straight into `trip_service.create_trip()` with no manual parsing.

**Why validate MIME type and size up front:** cheap, fast checks before spending an API call on an unsupported or oversized file — fails fast with a clear `400` instead of a confusing downstream error.

**Endpoint:** [`app/routers/voice.py`](app/routers/voice.py)
```python
@router.post("/trips", ...)
async def create_trip_from_voice(audio: UploadFile, ...):
    audio_bytes = await audio.read()
    trip_in = voice_service.transcribe_and_extract_trip(audio_bytes, audio.content_type)
    new_trip = trip_service.create_trip(db, trip_in, current_user.id)
    return {**new_trip.model_dump(), "message": "Trip create from voice input"}
```

---

## 8. Voice output: itinerary → spoken audio

**File:** [`app/services/voice_service.py`](app/services/voice_service.py)

Two steps:

**8a. Turning structured itinerary data into natural speech text:**
```python
def itinerary_to_speech_text(destination: str, days: list[dict]) -> str:
    lines = [f"Here is your {len(days)}-day itinerary for {destination}."]
    for day in days:
        lines.append(f"Day {day['day_number']}: {day['theme_or_focus']}.")
        for activity in day["activities"]:
            lines.append(f"At {activity['time']}, {activity['description']} at {activity['location']}.")
    return " ".join(lines)
```
This flattens the nested itinerary JSON (days → activities) into a single readable narration script, since a text-to-speech engine needs plain prose, not JSON.

**8b. Synthesizing audio from that text:**
```python
def synthesize_speech(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    try:
        subprocess.run(["espeak", "-w", tmp_path, text], check=True, capture_output=True)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.remove(tmp_path)
```
This shells out to the `espeak` command-line TTS engine, writing its output to a temporary `.wav` file, reading the bytes back into memory, and immediately deleting the temp file. **No audio is ever persisted to disk beyond the lifetime of a single request** — the bytes go straight into the HTTP response body.

**Why a local CLI tool instead of a cloud TTS API:** keeps this path free of an extra paid API dependency and extra network latency for a feature that's otherwise simple text-to-speech; the trade-off is `espeak`'s voice quality is noticeably more robotic than something like Google/ElevenLabs TTS, and `espeak` must be installed as a system package (it's not in `requirements.txt` since it isn't a Python package).

**Endpoint:** [`app/routers/voice.py`](app/routers/voice.py)
```python
@router.get("/itineraries/{trip_id}/audio")
def get_itinerary_audio(trip_id: int, ...):
    trip = trip_service.get_trip_by_id(db, trip_id=trip_id, owner_id=current_user.id)
    itinerary = itinerary_service.get_itinerary_by_trip_id(db, trip_id=trip_id)
    speech_text = voice_service.itinerary_to_speech_text(trip.destination, itinerary.days)
    audio_bytes = voice_service.synthesize_speech(speech_text)
    return Response(content=audio_bytes, media_type="audio/wav")
```
Ownership is checked the same way as every other trip/itinerary endpoint (`owner_id=current_user.id`), so a user can only ever request audio for their own itineraries.

**File:** [`app/main.py`](app/main.py) — the voice router is registered alongside the others:
```python
app.include_router(voice.router)
```

---

## 9. How this was tested

1. **MCP server standalone** — used `mcp dev app/mcp_servers/travel_tools_server.py` (MCP Inspector) to call `get_weather`, `find_places`, and `get_route` individually and confirm real data comes back.
2. **MCP client tool loading** — ran `load_mcp_tools()` directly to confirm all three tools are discovered and loaded with correct schemas.
3. **Full graph invocation** — built the graph and called it with a sample trip, confirming the agent actually calls the MCP tools and produces a complete structured itinerary. This is where the `invoke` vs `ainvoke` bug was caught and fixed.
4. **Full app walkthrough via Swagger (`/docs`)** — register → login → Authorize → create a trip → generate an itinerary (exercising the full MCP path through the real HTTP API) → fetch the saved itinerary → confirm conflict/auth/ownership edge cases (`409`, `401`, `404`).
5. **Voice audio endpoint** — called `GET /api/voice/itineraries/{trip_id}/audio` via Swagger and confirmed a valid, playable `audio/wav` response.

### Issues found and fixed during testing
- `psycopg2` wasn't in `requirements.txt`, breaking fresh installs — added `psycopg2-binary`.
- `graph.invoke()` crashed once MCP (async) tools were added — fixed by switching to `graph.ainvoke()` and propagating `async`/`await` through `llm_service.generate_itinerary_json` and the `create_itinerary` route.

### Known external dependency risk
`find_places` depends on the public Overpass API (`overpass-api.de`), which was observed to be unreliable/overloaded during testing (HTTP 406/504 from both the primary server and a mirror). The tool already fails gracefully (returns a string, doesn't crash the agent), but if `find_places` needs to be reliable in production, a paid places API or multi-mirror retry logic would be worth considering.
