# AI Vacation Planner

## Architecture Explanation

This project follows a decoupled, enterprise-grade RESTful architecture using **FastAPI**, **SQLModel**, and **PostgreSQL**. The codebase is strictly divided into distinct layers to enforce the Single Responsibility Principle, making it scalable and secure.

### Core Layers
* **Routing Layer (`app/routers/`)**: Acts as the traffic controller. Files like `trips.py` and `auth.py` define the API endpoints, handle HTTP requests, enforce security dependencies (like `get_current_user`), and format responses using Pydantic schemas.
* **Service Layer (`app/services/`)**: Contains the core business logic and database queries. Routers pass validated data to these services (e.g., `trip_service.py`), keeping the API layer lightweight and completely isolated from direct SQLAlchemy operations.
* **Data Validation (`app/models.py` & `schemas`)**: Utilizes Pydantic to strictly type-check incoming JSON payloads (Base, Create, Update) and format outgoing responses (Response models), automatically stripping sensitive data like password hashes.
* **Security Checkpoint (`app/oauth2.py` & `utils.py`)**: Implements OAuth2 with JWT (JSON Web Tokens). Every protected route requires a valid Bearer token. The system strictly enforces a **Private Data Model**, ensuring database queries mathematically restrict users to viewing and modifying only records tied to their specific `owner_id`.
* **Database Management (`alembic/`)**: Uses Alembic for version-controlled database migrations. Complex nested data, such as daily itinerary schedules, are natively mapped to PostgreSQL's highly efficient `JSONB` columns.
* **AI & Agentic Workflows (`app/agent/`, `app/services/llm_service.py`)**: Integrates large language models using a LangGraph agentic loop with native Tool Use. Rather than relying on string parsing, the LLM iteratively executes tools — a mix of in-process native tools and real-world tools loaded via the Model Context Protocol (MCP) — to gather context (like live weather, real places, and routes) and strictly structures its outputs via a `save_itinerary` tool whose schema is auto-generated from a dedicated Pydantic model (`ItineraryLLMOutput`), ensuring reliable and validated itinerary generation. See [Agent Tooling](#agent-tooling-native-tools-vs-mcp-tools) below for details.

### Agent Tooling: Native Tools vs. MCP Tools
The itinerary agent (`app/agent/graph.py`) is a LangGraph state machine built from two kinds of tools:

* **Native tools** (`app/agent/tools.py`) — plain LangChain `@tool`-decorated Python functions that run in-process, e.g. `search_travel_knowledge`, which queries the local RAG knowledge base.
* **MCP tools** (`app/mcp_servers/travel_tools_server.py`) — real-world tools (`get_weather`, `find_places`, `get_route`) exposed via the **Model Context Protocol (MCP)**. They run as a separate subprocess and communicate with the agent over stdio, which keeps tool implementations decoupled from the agent process and makes it easy to add or swap tool servers without touching agent code.

Both tool types are normalized into the same LangChain `Tool` interface via `langchain-mcp-adapters` (`app/agent/mcp_client.py`), so the agent graph treats them identically regardless of origin.

**Startup lifecycle:** spawning the MCP subprocess and loading its tools is an async operation, so the entire agent graph is built **once**, during the FastAPI app's `lifespan` startup (`init_itinerary_graph()` in `app/main.py`), rather than per request. Each request then reuses the already-built graph via `get_itinerary_graph()`, avoiding the overhead of spawning a new MCP subprocess on every itinerary generation call.

### RAG Knowledge Base (`app/knowledge_base/`)
This project includes a production-grade **Retrieval-Augmented Generation (RAG)** system that grounds AI-generated itineraries in real, curated travel knowledge rather than relying solely on the LLM's training data.

The system operates across two pipelines:

**Pipeline 1 — Indexing (run once, or when documents are updated):**
* `ingestion.py` — Loads raw `.txt` travel documents from `documents/` and wraps each file into a structured `TravelDocument` object.
* `chunking.py` — Splits each document into smaller overlapping text chunks (800 chars, 150 overlap) using `RecursiveCharacterTextSplitter`.
* `embedding.py` — Converts each chunk into a 384-dimensional semantic vector using the local `all-MiniLM-L6-v2` sentence transformer model.
* `vector_store.py` — Persists the vectors, raw text, and metadata tags (`destination`, `source`, `doc_type`) into a local ChromaDB vector database using HNSW + cosine similarity indexing.
* `pipeline.py` — Master runner that chains all four steps above into a single callable function.

**Pipeline 2 — Query (runs on every itinerary generation request):**
* `retrieval.py` — Embeds the user's destination query into a vector and performs a semantic similarity search against ChromaDB, with optional metadata filtering by destination.
* `context_assembler.py` — Formats the top retrieved chunks into a clearly labeled text block (bounded by `=== TRAVEL KNOWLEDGE BASE ===` markers) ready for LLM prompt injection.
* `llm_service.py` — Calls the context assembler before building the user prompt, injecting the retrieved knowledge at the top of the prompt. The LLM is explicitly instructed via a dedicated constraint to use the knowledge base when crafting the itinerary.

### Voice Integration (`app/services/voice_service.py`, `app/routers/voice.py`)
Users can create trips by speaking and listen to generated itineraries instead of only reading them.

* **Voice → Trip**: `POST /api/voice/trips` accepts an audio file, sends the raw audio bytes directly to a multimodal LLM (no separate transcription step) with `.with_structured_output(TripCreate)`, and creates a trip from the extracted destination, days, budget, and style — defaulting any field the speaker didn't mention.
* **Itinerary → Audio**: `GET /api/voice/itineraries/{trip_id}/audio` converts a saved itinerary into natural narration text, synthesizes it to speech via the `espeak` CLI, and streams the resulting `audio/wav` bytes directly in the response. No audio file is ever persisted to disk — it exists only for the duration of the request.

---

## LLM Integration

This project is **provider-agnostic**: the LLM provider and model are configuration, not code. Both the itinerary agent and the voice features read their provider/model from environment variables via `app/config.py`, and the agent is built using LangChain's `init_chat_model()`, which dispatches to the correct provider's chat model class at runtime.

### Supported providers
| Provider | `LLM_PROVIDER` value | Required key |
|---|---|---|
| Google (Gemini) | `google_genai` *(default)* | `GOOGLE_API_KEY` |
| Anthropic (Claude) | `anthropic` | `ANTHROPIC_API_KEY` |

### Relevant environment variables
* `LLM_PROVIDER` — which provider powers the itinerary agent's tool-calling loop (`app/agent/graph.py`).
* `LLM_MODEL` — the specific model ID used by the itinerary agent (must belong to `LLM_PROVIDER`).
* `VOICE_LLM_MODEL` — the model used for voice trip extraction (`app/services/voice_service.py`). This must support multimodal audio input, since raw audio bytes are sent directly to it rather than pre-transcribed text.
* `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` — only the key matching your chosen provider(s) is required; set both if you want the flexibility to switch without redeploying.

### Switching providers
To switch the itinerary agent from Gemini to Claude (or vice versa), update `LLM_PROVIDER` and `LLM_MODEL` in your `.env` file and restart the server — no code changes required.

---

## Setup Instructions

Follow these step-by-step instructions to get the backend running in your local development environment.

### 1. Set Up the Virtual Environment
Ensure you are in the root directory of the project, then create and activate a Python virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
Install all required Python packages (including FastAPI, SQLModel, Alembic, Passlib, ChromaDB, sentence-transformers, LangChain/LangGraph, and the MCP SDK):
```bash
pip install -r requirements.txt
```

### 3. Install System Dependencies (for Voice Features)
The itinerary-to-audio feature shells out to the `espeak` command-line text-to-speech engine, which is a system package, not a Python one:
```bash
sudo apt-get install espeak
```

### 4. Create the PostgreSQL Database
Ensure your local PostgreSQL service is running:
```bash
sudo service postgresql start
```
Before running migrations, you must create the blank database. Log into PostgreSQL and create it:
```bash
sudo -u postgres psql -c "CREATE DATABASE vacation_planner;"
```

### 5. Configure Environment Variables
Create a `.env` file in the root directory of your project based on the provided `.env.example`. At minimum, set `DATABASE_URL`, `SECRET_KEY`, and the API key for whichever LLM provider you choose (see [LLM Integration](#llm-integration) above for provider/model options).

### 6. Run Database Migrations
```bash
alembic upgrade head
```

### 7. Run the RAG Indexing Pipeline
Before starting the server, populate the local vector database with the travel knowledge base. This only needs to be run once (or whenever you add new documents to `app/knowledge_base/documents/`):
```bash
python -c "from app.knowledge_base.pipeline import run_indexing_pipeline; run_indexing_pipeline()"
```
Expected output: `Indexed 1826 chunks into 'travel_knowledge_base'.`

### 8. Start the Development Server
```bash
fastapi dev app/main.py
```
On startup, the app builds the itinerary agent's graph once — including spawning the MCP tools subprocess — before accepting requests. Check the startup logs for a clean `Application startup complete.` with no tracebacks.

---

## Adding New Travel Knowledge
To add new destinations to the knowledge base:
1. Create a plain `.txt` file named after the destination (e.g., `barcelona.txt`) inside `app/knowledge_base/documents/`.
2. Re-run the indexing pipeline command from Step 7 above. The pipeline uses `upsert`, so existing documents are safely updated without creating duplicates.