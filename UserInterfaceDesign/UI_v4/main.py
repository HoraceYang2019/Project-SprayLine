from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI(title="Spraying Line Monitoring System")

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "spraying_dashboard_updated.html"

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

@app.get("/", response_class=HTMLResponse)
def home():
    if not HTML_FILE.exists():
        return HTMLResponse(
            content=(
                "<h2>找不到 spraying_dashboard_updated.html</h2>"
                "<p>請先執行 spraying_dashboard_updated_fixed_v4.py，"
                "或確認 main.py 和 spraying_dashboard_updated.html 放在同一個資料夾。</p>"
            ),
            status_code=404,
            headers=NO_CACHE_HEADERS,
        )

    return FileResponse(
        HTML_FILE,
        media_type="text/html; charset=utf-8",
        headers=NO_CACHE_HEADERS,
    )

@app.get("/spraying_dashboard_updated.html")
def dashboard_html():
    return home()
