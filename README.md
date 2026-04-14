# Trade News

Trade News is a decision-support app that converts market news into explainable investment signals.

## Week 1 Scope
- FastAPI service skeleton
- Health endpoint
- Baseline folder layout for ingestion, scoring, alerts, and dashboard

## Quick Start
1. Create and activate a Python 3.11+ environment.
2. Install dependencies:
   - `pip install -e .`
3. Run the API:
   - `python -m uvicorn api.main:app --reload`
4. Open health check:
   - `http://127.0.0.1:8000/health`

## Database and Migrations
1. Start PostgreSQL:
   - `docker compose -f infra/docker-compose.yml up -d`
2. Create local environment file:
   - copy `.env.example` to `.env`
3. Run initial migration:
   - `alembic upgrade head`

## Stop Local Services
- `docker compose -f infra/docker-compose.yml down`

## Project Structure
- api/
- ingestion/
- scoring/
- alerts/
- dashboard/
- infra/
- tests/
