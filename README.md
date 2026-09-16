# AI Vacation Planner

## Architecture Explanation

This project follows a decoupled, enterprise-grade RESTful architecture using **FastAPI**, **SQLModel**, and **PostgreSQL**. The codebase is strictly divided into distinct layers to enforce the Single Responsibility Principle, making it scalable and secure.

### Core Layers
* **Routing Layer (`app/routers/`)**: Acts as the traffic controller. Files like `trips.py` and `auth.py` define the API endpoints, handle HTTP requests, enforce security dependencies (like `get_current_user`), and format responses using Pydantic schemas.
* **Service Layer (`app/services/`)**: Contains the core business logic and database queries. Routers pass validated data to these services (e.g., `trip_service.py`), keeping the API layer lightweight and completely isolated from direct SQLAlchemy operations.
* **Data Validation (`app/models.py` & `schemas`)**: Utilizes Pydantic to strictly type-check incoming JSON payloads (Base, Create, Update) and format outgoing responses (Response models), automatically stripping sensitive data like password hashes.
* **Security Checkpoint (`app/oauth2.py` & `utils.py`)**: Implements OAuth2 with JWT (JSON Web Tokens). Every protected route requires a valid Bearer token. The system strictly enforces a **Private Data Model**, ensuring database queries mathematically restrict users to viewing and modifying only records tied to their specific `owner_id`.
* **Database Management (`alembic/`)**: Uses Alembic for version-controlled database migrations. Complex nested data, such as daily itinerary schedules, are natively mapped to PostgreSQL's highly efficient `JSONB` columns.
* **AI & Agentic Workflows (`app/services/llm_service.py`)**: Integrates large language models using an agentic loop with native Tool Use. Rather than relying on string parsing, the LLM iteratively executes tools to gather context (like live weather) and strictly structures its outputs via a `save_itinerary` tool whose schema is auto-generated from a dedicated Pydantic model (`ItineraryLLMOutput`), ensuring reliable and validated itinerary generation.

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
Install all required Python packages (including FastAPI, SQLModel, Alembic, Passlib, ChromaDB, and sentence-transformers):
```bash
pip install -r requirements.txt
```

### 3. Create the PostgreSQL Database
Ensure your local PostgreSQL service is running:
```bash
sudo service postgresql start
```
Before running migrations, you must create the blank database. Log into PostgreSQL and create it:
```bash
sudo -u postgres psql -c "CREATE DATABASE vacation_planner;"
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory of your project based on the provided `.env.example`.

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Run the RAG Indexing Pipeline
Before starting the server, populate the local vector database with the travel knowledge base. This only needs to be run once (or whenever you add new documents to `app/knowledge_base/documents/`):
```bash
python -c "from app.knowledge_base.pipeline import run_indexing_pipeline; run_indexing_pipeline()"
```
Expected output: `Indexed 1826 chunks into 'travel_knowledge_base'.`

### 7. Start the Development Server
```bash
fastapi dev app/main.py
```

---

## Adding New Travel Knowledge
To add new destinations to the knowledge base:
1. Create a plain `.txt` file named after the destination (e.g., `barcelona.txt`) inside `app/knowledge_base/documents/`.
2. Re-run the indexing pipeline command from Step 6 above. The pipeline uses `upsert`, so existing documents are safely updated without creating duplicates.