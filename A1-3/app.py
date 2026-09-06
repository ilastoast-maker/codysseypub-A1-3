from pathlib import Path

from fastapi.responses import FileResponse

from api.index import app


PROJECT_ROOT = Path(__file__).resolve().parent
INDEX_FILE = PROJECT_ROOT / "index.html"


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    """Serve the single-page frontend from the same FastAPI deployment."""
    return FileResponse(INDEX_FILE, media_type="text/html")
