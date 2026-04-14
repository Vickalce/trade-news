from fastapi import FastAPI

from .routes import execution, health, pipeline, validation

app = FastAPI(title="Trade News", version="0.1.0")
app.include_router(health.router)
app.include_router(pipeline.router)
app.include_router(validation.router)
app.include_router(execution.router)
