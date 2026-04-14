# Trade News

Trade News is a decision-support app that converts market news into explainable investment signals.

## MVP Features
- Multi-source RSS ingestion with deduplication
- Entity extraction and scope classification
- Symbol and sector-proxy mapping
- Provider abstraction for news and market data
- Live market quote reaction from Yahoo Finance with deterministic fallback provider
- Composite scoring and recommendation engine
- Email, Discord, and Telegram alert channels (with local outbox fallback)
- API key protection and request rate limiting on signal endpoints
- Paper validation endpoint for signal quality checks
- Streamlit operator dashboard

## Quick Start
1. Create and activate a Python 3.11+ environment.
2. Install dependencies:
   - `pip install -e .`
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

## Pipeline Flow
1. Ingest latest events:
   - `POST /pipeline/ingest` with header `x-api-key` when `API_KEY` is set
2. Generate signals:
   - `POST /pipeline/run?limit=20` with header `x-api-key`
3. Read recommendations:
   - `GET /pipeline/recommendations?limit=50` with header `x-api-key`
4. Check paper metrics:
   - `GET /validation/paper?limit=200` with header `x-api-key`

## Providers
Configure providers in `.env`:
- `NEWS_PROVIDER=rss` or `demo`
- `MARKET_DATA_PROVIDER=yahoo` or `fallback`

Provider tuning:
- `NEWS_TIMEOUT_SECONDS`
- `MAX_FEED_ITEMS_PER_SOURCE`
- `MARKET_DATA_TIMEOUT_SECONDS`

## Alert Channels
Configure one or more channels in `.env` using `ALERT_CHANNELS_CSV`:
- `email`
- `discord`
- `telegram`

Example:
- `ALERT_CHANNELS_CSV=email,discord,telegram`

If a channel is not configured, alerts are written to `alerts/outbox`.

## Security and Limits
Set optional API and throttling controls:
- `API_KEY`
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_MAX_REQUESTS`

## Dashboard
Run:
- `streamlit run dashboard/app.py`

The dashboard shows recommendation history and confidence summaries.

## Scheduler (Optional)
Run background ingestion and scoring every 5 minutes:
- `python -m api.jobs.scheduler`

## Stop Local Services
- `docker compose -f infra/docker-compose.yml down`

## CI
GitHub Actions CI runs tests on push/PR via [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Project Structure
- api/
- ingestion/
- scoring/
- alerts/
- dashboard/
- infra/
- tests/
