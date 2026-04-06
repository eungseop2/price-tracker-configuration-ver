import os
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .main import run_once
from .gcs_sync import upload_db, download_db

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("tracker.cloud")

app = FastAPI(title="Naver Price Tracker Cloud")

# Configuration from ENV
CONFIG_PATH = os.getenv("CONFIG_PATH", "targets.yaml")
DB_PATH = os.getenv("DB_PATH", "data/price_tracker.sqlite3")
ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "data/artifacts")
GCS_BUCKET = os.getenv("GCS_BUCKET") # GCS 踰꾪궥 ?대쫫 (?꾩닔)
INTERVAL = int(os.getenv("COLLECT_INTERVAL", "3600"))
ENABLE_BACKGROUND_COLLECTION = os.getenv("ENABLE_BACKGROUND_COLLECTION", "false").lower() == "true"
ENABLE_MANUAL_COLLECT = os.getenv("ENABLE_MANUAL_COLLECT", "false").lower() == "true"
ENABLE_GCS_SYNC = os.getenv("ENABLE_GCS_SYNC", "false").lower() == "true"

# ?뺤쟻 ?뚯씪 ?쒕튃 (dashboard_data.json ??
app.mount("/static", StaticFiles(directory="."), name="static")

@app.on_event("startup")
async def startup_event():
    """???쒖옉 ??GCS?먯꽌 DB ?ㅼ슫濡쒕뱶 諛?異붿쟻 猷⑦봽 ?쒖옉"""
    logger.info("Cloud App starting up (Read-Only Mode Default)...")
    
    # 1. GCS?먯꽌 理쒖떊 DB ?ㅼ슫濡쒕뱶
    if GCS_BUCKET and ENABLE_GCS_SYNC:
        download_db(GCS_BUCKET, DB_PATH)
    
    # 2. 諛깃렇?쇱슫??異붿쟻 猷⑦봽 ?쒖옉
    if ENABLE_BACKGROUND_COLLECTION:
        asyncio.create_task(tracker_loop())
    else:
        logger.info("Background collection is disabled by default.")

async def update_tracker_data():
    """?섏쭛 ?섑뻾 諛?UI/GCS 媛깆떊 濡쒖쭅"""
    try:
        logger.info("Starting collection and sync...")
        ok, fail = await run_once(CONFIG_PATH, DB_PATH, ARTIFACTS_DIR)
        logger.info(f"Collection finished: ok={ok}, fail={fail}")
        
        # export-ui 濡쒖쭅 ?댁옣: JSON ?뚯씪留??앹꽦?섎룄濡?蹂寃?(HTML 二쇱엯 ?쒓굅)
        from .config import load_config
        app_config = load_config(CONFIG_PATH)
        categories = {t.name: t.category for t in app_config.targets}

        store = ObservationStore(DB_PATH)
        data = store.get_dashboard_data(categories=categories)
        store.close()
        
        # dashboard_data.json ?먯옄??湲곕줉 (Race Condition 諛⑹?)
        json_path = Path("dashboard_data.json")
        tmp_path = json_path.with_name(json_path.name + ".tmp")
        tmp_path.write_text(dump_json(data), encoding="utf-8")
        tmp_path.replace(json_path)
        
        logger.info("dashboard_data.json updated.")
        
        # 3. GCS濡?寃곌낵 ?낅줈??
        if GCS_BUCKET and ENABLE_GCS_SYNC:
            upload_db(GCS_BUCKET, DB_PATH)
        return ok, fail
    except Exception as e:
        logger.error(f"Update error: {e}")
        raise e

async def tracker_loop():
    """諛곌꼍?먯꽌 二쇨린?곸쑝濡??섏쭛 ?섑뻾"""
    error_count = 0
    while True:
        try:
            await update_tracker_data()
            error_count = 0
        except Exception as e:
            error_count += 1
            logger.error(f"Tracker loop execution error: {e}")
            
        penalty = min(600, error_count * 60) if error_count > 0 else 0
        sleep_for = INTERVAL + penalty
        if error_count > 0:
            logger.warning(f"?곗냽 ?먮윭 {error_count}?? ?湲?{sleep_for}珥?(諛깆삤??{penalty}珥?")
            
        await asyncio.sleep(sleep_for)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """??쒕낫??蹂닿린"""
    html_path = Path("dashboard.html")
    if html_path.exists():
        # dashboard.html ?대??먯꽌 fetch('dashboard_data.json') ?먮뒗 fetch('/dashboard_data.json') ?몄텧 ????꾩슂
        return html_path.read_text(encoding="utf-8")
    return HTMLResponse("Dashboard not found. Run collection first or check if dashboard.html exists.", status_code=404)

@app.get("/dashboard_data.json")
async def get_dashboard_data():
    """??쒕낫???곗씠??JSON ?쒕튃"""
    json_path = Path("dashboard_data.json")
    if json_path.exists():
        return FileResponse(json_path)
    raise HTTPException(status_code=404, detail="Data not found")

@app.post("/collect")
async def manual_collect():
    """?섎룞 ?섏쭛 ?몃━嫄?""
    if not ENABLE_MANUAL_COLLECT:
        return {"status": "error", "message": "Manual collection is disabled. Set ENABLE_MANUAL_COLLECT=true"}
    ok, fail = await update_tracker_data()
    return {"status": "ok", "ok": ok, "fail": fail}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

