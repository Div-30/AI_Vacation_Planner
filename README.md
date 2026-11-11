# AI Vacation Planner

## Architecture Explanation

This project follows a decoupled, enterprise-grade RESTful architecture using **FastAPI**, **SQLModel**, and **PostgreSQL**. The codebase is strictly divided into distinct layers to enforce the Single Responsibility Principle, making it scalable and secure.

### Core Layers

- **Routing Layer (`app/routers/`)**: Acts as the traffic controller. Files like `trips.py`, `itineraries.py`, and `auth.py` define API endpoints, handle HTTP requests, enforce security dependencies (like `get_current_user`), and format responses using Pydantic schemas.
- **Service Layer (`app/services/`)**: Contains core business logic and database queries (e.g., `trip_service.py`, `itinerary_service.py`), keeping routers lightweight and decoupled from direct database operations.
- **Data Validation (`app/models.py`)**: Utilizes SQLModel and Pydantic to strictly type-check incoming JSON payloads and format outgoing responses, automatically stripping sensitive data like password hashes.
- **Security & Data Isolation (`app/oauth2.py` & `app/utils.py`)**: Implements OAuth2 with JWT (JSON Web Tokens). Every protected route requires a valid Bearer token, strictly enforcing tenancy isolation so users can access and modify only records matching their `owner_id`.
- **Database Management (`alembic/`)**: Uses Alembic for version-controlled database migrations. Complex nested itinerary schedules are natively stored using PostgreSQL `JSONB` columns.

### Agentic Loop & Tooling (`app/agent/`)

The itinerary generation system is powered by a stateful agent graph built with **LangGraph**:

- **State Machine Flow (`app/agent/graph.py`)**: Executes a cyclic graph `START -> agent -> (tools | finalize) -> agent -> END`. The agent iteratively executes tools until it calls `save_itinerary` once ready to submit the validated itinerary.
- **Native Tools (`app/agent/tools.py`)**: In-process LangChain tools such as `search_travel_knowledge`, which queries the local ChromaDB vector store.
- **MCP Tools (`app/mcp_servers/travel_tools_server.py`)**: Real-world external tools (`get_weather`, `find_places`, `get_route`) exposed via the **Model Context Protocol (MCP)**. They run in a separate subprocess communicating over stdio via `langchain-mcp-adapters`, keeping tool implementations decoupled from the core application.
- **Agent Observability (`app/agent/observability.py`)**: Tracks agent executions with `AgentObservabilityCallback`, capturing end-to-end latency, prompt/completion token consumption, active model names, tool call counts, and execution errors.

### RAG Knowledge Base (`app/knowledge_base/`)

This project includes a production-grade **Retrieval-Augmented Generation (RAG)** system that grounds AI-generated itineraries in real, curated travel knowledge:

- **Indexing Pipeline (`app/knowledge_base/pipeline.py`)**: Ingests `.txt` travel documents, chunks text with `RecursiveCharacterTextSplitter` (800 chars, 150 overlap), generates 384-dimensional semantic embeddings using `all-MiniLM-L6-v2`, and persists vectors to a local ChromaDB collection using HNSW + cosine similarity.
- **Retrieval Pipeline (`app/knowledge_base/retrieval.py` & `context_assembler.py`)**: Queries ChromaDB with semantic search and formats top retrieved chunks into structured context blocks for the agent's knowledge retrieval tool.

### Voice Integration (`app/services/voice_service.py`, `app/routers/voice.py`)

- **Voice → Trip**: `POST /api/voice/trips` accepts an audio file, sends raw audio bytes directly to a multimodal LLM with `.with_structured_output(TripCreate)`, and creates a trip without a separate transcription step.
- **Itinerary → Audio**: `GET /api/voice/itineraries/{trip_id}/audio` converts a saved itinerary into natural narration text and streams synthesized `audio/wav` bytes directly via the `espeak` CLI without persisting files to disk.

---

## LLM Integration

The application is provider-agnostic: the LLM provider and model are configuration, not code. Both the itinerary agent and voice features read configuration from environment variables via `app/config.py`, using LangChain's `init_chat_model()` to dispatch to the correct chat model class at runtime.

### Supported Providers

| Provider           | `LLM_PROVIDER` value       | Required key        |
| ------------------ | -------------------------- | ------------------- |
| Google (Gemini)    | `google_genai` _(default)_ | `GOOGLE_API_KEY`    |
| Anthropic (Claude) | `anthropic`                | `ANTHROPIC_API_KEY` |

### Integration Details

- **Structured Output Enforcement**: Instead of fragile JSON string parsing, the agent binds tools with `tool_choice="any"` and structures output through a specialized `save_itinerary` tool whose schema is auto-generated from the `ItineraryLLMOutput` Pydantic model.
- **Multimodal Audio Support**: Voice trip extraction streams raw audio bytes directly into Gemini's multimodal LLM (`ChatGoogleGenerativeAI`). Therefore, `GOOGLE_API_KEY` is always required for voice features, even when `LLM_PROVIDER=anthropic`.
- **Provider Switching**: Switch providers simply by updating `LLM_PROVIDER` and `LLM_MODEL` in `.env` and restarting the server—no code changes required.

---

## Security and Guardrails

The application enforces multi-layered defense across user requests and LLM generation (`app/services/guardrails.py`):

- **Pre-Execution Guardrails (`validate_input_safety`)**:
  - **Constraint Validation**: Enforces duration limits (1–30 days), positive budgets, and valid destination strings.
  - **Prompt Injection Defense**: Evaluates inputs against regex patterns (`PROMPT_INJECTION_PATTERNS`) targeting system prompt leaks, jailbreaks, and instructions override (e.g., `"ignore previous instructions"`, `"DAN mode"`, `"developer mode"`), raising HTTP 400 on detection.
- **Post-Execution Guardrails (`validate_output_safety`)**:
  - **Schema Validation**: Validates the agent output dictionary against `ItineraryLLMOutput`.
  - **Duration Consistency**: Verifies that the number of days generated strictly matches the requested duration.
  - **Schedule Completeness**: Ensures that every generated day contains non-empty scheduled activities before committing to the database.
- **Tenant Isolation & Access Control**: Protected routes enforce OAuth2 Bearer token authentication (`app/oauth2.py`), mathematically restricting database queries to records matching the authenticated user's `owner_id`.

---

## Evaluation Approach

The project leverages [DeepEval](https://github.com/confident-ai/deepeval) for automated LLM-as-a-judge evaluation of generated itineraries (`app/evaluation/`):

- **Evaluation Dataset (`app/evaluation/dataset.py`)**: Golden test cases covering diverse destinations, durations, and budget tiers.
- **Evaluation Metrics (`app/evaluation/metrics.py`)**:
  - **Itinerary Relevance (`GEval`)**: Measures destination matching, travel style alignment, and budget realism using explicit domain rubrics.
  - **Itinerary Completeness (`GEval`)**: Verifies day counts, structured time slots (morning, afternoon, evening), locations, and realistic activity durations.
  - **Task Completion (`TaskCompletionMetric`)**: Validates that the agent fulfills the overarching goal of generating a realistic, geographically valid, and budget-aligned itinerary.
- **Running Evaluations**:
  ```bash
  python app/evaluation/evaluate_itinerary.py
  ```

---

## Testing Strategy

Automated test suites are managed with `pytest` under `app/tests/`:

- **Guardrail Tests (`app/tests/test_guardrails.py`)**: Verifies that `validate_input_safety` blocks prompt injections, excessive day counts, and invalid budgets while allowing legitimate requests.
- **Structured Output Schema Tests (`app/tests/test_structured_output.py`)**: Tests that `ItineraryLLMOutput` properly validates conformant itinerary payloads and rejects invalid schemas or missing fields.
- **Running Tests**:
  ```bash
  pytest -v
  ```

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

Create a `.env` file in the root directory of your project based on the provided `.env.example`. At
minimum, set `DATABASE_URL`, `SECRET_KEY`, and the API key for your chosen itinerary LLM provider. If
using the voice endpoints, `GOOGLE_API_KEY` is always required for multimodal voice extraction.

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

On startup, the app builds the itinerary agent's graph once — discovering and binding the MCP tools —
before accepting requests. Check the startup logs for a clean `Application startup complete.` with no
tracebacks.

---

## Adding New Travel Knowledge

To add new destinations to the knowledge base:

1. Create a plain `.txt` file named after the destination (e.g., `barcelona.txt`) inside `app/knowledge_base/documents/`.
2. Re-run the indexing pipeline command from Step 7 above. The pipeline uses `upsert`, so existing documents are safely updated without creating duplicates.
