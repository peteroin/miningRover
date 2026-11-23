
import os, asyncio
from datetime import datetime, timezone
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("CONSENTIUM_BASE_URL", "https://api.consentiumiot.com").rstrip("/")
RECEIVE_KEY = os.getenv("CONSENTIUM_RECEIVE_KEY", "").strip()
BOARD_KEY = os.getenv("CONSENTIUM_BOARD_KEY", "").strip()
POLL_SECONDS = max(3, int(os.getenv("POLL_SECONDS", "5")))
HISTORY_LIMIT = max(10, int(os.getenv("HISTORY_LIMIT", "1000")))

app = FastAPI(title="Consentium Gas Rover Heatmap", version="1.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
cache: dict[str, Any] = {"board": {}, "feeds": [], "latest": None,
                          "last_success": None, "last_error": None}

def num(v):
    try:
        if v is None or v == "": return None
        n = float(v)
        return None if n <= -999 else n
    except (TypeError, ValueError):
        return None

def extract_labels(board):
    labels = {}
    for k, v in (board or {}).items():
        if str(k).startswith("info") and v is not None:
            labels[str(k).replace("info", "value", 1)] = str(v)
    return labels

def normalize_feed(feed: dict, labels: dict) -> dict:
    raw = {"timestamp": feed.get("updated_at", feed.get("timestamp"))}
    for value_key, value in feed.items():
        if value_key in ("updated_at", "timestamp"): continue
        raw[labels.get(value_key, value_key)] = value

    # Exact labels emitted by the user's uploaded ESP32 firmware, plus older aliases.
    aliases = {
      "mq4_raw": ["MQ4_ADC_RAW", "MQ4_ADC", "MQ4_RAW"],
      "mq7_raw": ["MQ7_ADC_RAW", "MQ7_ADC", "MQ7_RAW"],
      "mq4_norm": ["MQ4_RESPONSE_NORMALIZED", "MQ4_NORM"],
      "mq7_norm": ["MQ7_RESPONSE_NORMALIZED", "MQ7_NORM"],
      "temperature": ["Temperature_C", "Temperature"],
      "humidity": ["Humidity_percent", "Humidity_Percent", "Humidity"],
      "distance_cm": ["Ultrasonic_cm", "Distance_cm", "Distance"],
      "x_m": ["Position_X_East_m", "Position_X_m", "X_m"],
      "y_m": ["Position_Y_North_m", "Position_Y_m", "Y_m"],
      "heading_deg": ["Heading_deg", "Heading_Deg", "Heading"],
      "latitude": ["Latitude_est", "Latitude"],
      "longitude": ["Longitude_est", "Longitude"],
      "encoder_left": ["Encoder_Left_Ticks", "Encoder_Left"],
      "encoder_right": ["Encoder_Right_Ticks", "Encoder_Right"],
      "origin_set": ["Origin_Set"],
      "mpu1_ok": ["MPU1_OK"],
      "mpu2_ok": ["MPU2_OK"],
    }
    lower = {str(k).strip().lower(): v for k, v in raw.items()}
    def find(names):
        for name in names:
            if name.lower() in lower: return lower[name.lower()]
        return None

    out = dict(raw)
    for key, names in aliases.items():
        value = find(names)
        out[key] = num(value)
    # Prefer normalized values sent by firmware; otherwise scale raw 12-bit ADC.
    if out["mq4_norm"] is None and out["mq4_raw"] is not None:
        out["mq4_norm"] = max(0.0, min(1.0, out["mq4_raw"] / 4095.0))
    if out["mq7_norm"] is None and out["mq7_raw"] is not None:
        out["mq7_norm"] = max(0.0, min(1.0, out["mq7_raw"] / 4095.0))
    return out

async def api_get(recents=False):
    if not RECEIVE_KEY or not BOARD_KEY:
        raise RuntimeError("Set CONSENTIUM_RECEIVE_KEY and CONSENTIUM_BOARD_KEY in .env")
    params = {"receiveKey": RECEIVE_KEY, "boardKey": BOARD_KEY}
    if recents: params["recents"] = "true"
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
        r = await client.get(f"{BASE_URL}/getData", params=params)
        if r.is_error:
            raise RuntimeError(f"Consentium API HTTP {r.status_code}: {r.text[:300]}")
        payload = r.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected Consentium response; expected JSON object")
        return payload

def parse_payload(payload):
    board = payload.get("board") or {}
    feeds = payload.get("feeds") or []
    labels = extract_labels(board)
    rows = [normalize_feed(f, labels) for f in feeds if isinstance(f, dict)]
    rows.sort(key=lambda x: str(x.get("timestamp") or ""))
    return board, rows

async def refresh_history():
    try:
        payload = await api_get(False)
        board, rows = parse_payload(payload)
        cache.update(board=board, feeds=rows[-HISTORY_LIMIT:],
                     latest=rows[-1] if rows else None,
                     last_success=datetime.now(timezone.utc).isoformat(), last_error=None)
    except Exception as e:
        cache["last_error"] = str(e)

async def poll_latest():
    while True:
        try:
            payload = await api_get(True)
            board, rows = parse_payload(payload)
            if board: cache["board"] = board
            if rows:
                latest = rows[-1]
                old = cache.get("latest")
                if not old or latest.get("timestamp") != old.get("timestamp"):
                    cache["feeds"].append(latest)
                    cache["feeds"] = cache["feeds"][-HISTORY_LIMIT:]
                cache["latest"] = latest
            cache["last_success"] = datetime.now(timezone.utc).isoformat()
            cache["last_error"] = None
        except Exception as e:
            cache["last_error"] = str(e)
        await asyncio.sleep(POLL_SECONDS)

@app.on_event("startup")
async def startup():
    await refresh_history()
    asyncio.create_task(poll_latest())

@app.get("/")
async def home(): return FileResponse("static/index.html")

@app.get("/api/telemetry")
async def telemetry():
    return {"board": cache["board"], "feeds": cache["feeds"], "latest": cache["latest"],
            "last_success": cache["last_success"], "last_error": cache["last_error"],
            "poll_seconds": POLL_SECONDS, "configured": bool(RECEIVE_KEY and BOARD_KEY)}

@app.post("/api/reload")
async def reload():
    await refresh_history()
    if cache["last_error"]: raise HTTPException(502, cache["last_error"])
    return {"ok": True, "count": len(cache["feeds"])}

@app.get("/health")
async def health():
    return {"ok": True, "configured": bool(RECEIVE_KEY and BOARD_KEY)}
