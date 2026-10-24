import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ml.classifier import classify, load_model, to_coarse

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Settings come from environment variables (see .env.example)
MODEL_PATH = Path(os.getenv("MODEL_PATH", "final_model.joblib"))
if not MODEL_PATH.is_absolute():
    MODEL_PATH = BASE_DIR / MODEL_PATH
APP_VERSION = os.getenv("APP_VERSION", "dev")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model(MODEL_PATH)  # load the model once, at startup
    yield


app = FastAPI(title="Shadow-ml Classifier API", version=APP_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ClassifyRequest(BaseModel):
    text: str


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.post("/api/classify")
def classify_text(req: ClassifyRequest):
    try:
        result = classify(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result["coarse_label"] = to_coarse(result["label"])
    return result
