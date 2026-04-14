# Trade News

Trade News is a decision-support app that converts market news into explainable investment signals.

## Week 1 Scope
## MVP Features
- Multi-source RSS ingestion with deduplication
- Entity extraction and scope classification
- Symbol and sector-proxy mapping
- Reaction feature generation and market snapshot persistence
- Composite scoring and recommendation engine
- Alert delivery stubs with cooldown and daily limits
- Paper validation endpoint for signal quality checks
- Streamlit operator dashboard
## Quick Start
1. Create and activate a Python 3.11+ environment.
2. Install dependencies:
   - `pip install -e .`
3. Run the API:
3. Create local environment file:
   - copy `.env.example` to `.env`
4. Start PostgreSQL:
   - `docker compose -f infra/docker-compose.yml up -d`
5. Run migrations:
   - `alembic upgrade head`
6. Run the API:
   - `python -m uvicorn api.main:app --reload`
7. Open health check:
   - `http://127.0.0.1:8000/health`
   - `python -m uvicorn api.main:app --reload`
## Pipeline Flow
1. Ingest latest events:
   - `POST /pipeline/ingest`
2. Generate signals:
   - `POST /pipeline/run?limit=20`
3. Read recommendations:
   - `GET /pipeline/recommendations?limit=50`
4. Check paper metrics:
   - `GET /validation/paper?limit=200`
1. Start PostgreSQL:
## Dashboard
Run:
- `streamlit run dashboard/app.py`

The dashboard shows recommendation history and confidence summaries.

## Scheduler (Optional)
Run background ingestion and scoring every 5 minutes:
- `python -m api.jobs.scheduler`
- `docker compose -f infra/docker-compose.yml down`

## Project Structure
- api/
- ingestion/
- scoring/
- alerts/
- dashboard/
- infra/
- tests/
