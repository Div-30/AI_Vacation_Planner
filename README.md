# AI Vacation Planner

## Architecture Explanation

This project follows a decoupled, enterprise-grade RESTful architecture using **FastAPI**, **SQLModel**, and **PostgreSQL**. The codebase is strictly divided into distinct layers to enforce the Single Responsibility Principle, making it scalable and secure.

### Core Layers
* **Routing Layer (`app/routers/`)**: Acts as the traffic controller. Files like `trips.py` and `auth.py` define the API endpoints, handle HTTP requests, enforce security dependencies (like `get_current_user`), and format responses using Pydantic schemas. 
* **Service Layer (`app/services/`)**: Contains the core business logic and database queries. Routers pass validated data to these services (e.g., `trip_service.py`), keeping the API layer lightweight and completely isolated from direct SQLAlchemy operations.
* **Data Validation (`app/models.py` & `schemas`)**: Utilizes Pydantic to strictly type-check incoming JSON payloads (Base, Create, Update) and format outgoing responses (Response models), automatically stripping sensitive data like password hashes.
* **Security Checkpoint (`app/oauth2.py` & `utils.py`)**: Implements OAuth2 with JWT (JSON Web Tokens). Every protected route requires a valid Bearer token. The system strictly enforces a **Private Data Model**, ensuring database queries mathematically restrict users to viewing and modifying only records tied to their specific `owner_id`.
* **Database Management (`alembic/`)**: Uses Alembic for version-controlled database migrations. Complex nested data, such as daily itinerary schedules, are natively mapped to PostgreSQL's highly efficient `JSONB` columns.

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
Install all required Python packages (including FastAPI, SQLModel, Alembic, Passlib, and Uvicorn):
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
Create a .env file in the root directory of your project

### 5. Run Database Migrations
```bash
alembic upgrade head
```
### 6. Start the Development Server
```bash
fastapi dev app/main.py
```