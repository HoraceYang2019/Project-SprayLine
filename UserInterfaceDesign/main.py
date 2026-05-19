
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

@app.get("/", response_class=HTMLResponse)
def home():
    html_path = BASE_DIR / "spraying_dashboard.html"
    return html_path.read_text(encoding="utf-8")
