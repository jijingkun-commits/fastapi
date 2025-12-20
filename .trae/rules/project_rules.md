# Project Rules for Trae

- Use FastAPI `lifespan` for startup/shutdown; avoid `@app.on_event`.
- Prefer absolute imports: `from app...` across the project.
- Register new endpoints via `app/api/v1/router.py`.
- Run tests: `python -m pytest -q`.
- Start dev server: `uvicorn app.main:app --reload --port 8000`.
- Use `.env` and `python-dotenv` for configuration.
- Use Pydantic v2 style (`ConfigDict`) for model config.
