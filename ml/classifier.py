"""
Shadow AI Security & DLP Gateway — ML inference module
======================================================================
This is the function Devansh's FastAPI backend calls. Per the SRS's
ML contract: submitted text in, {label, confidence} out.

ONE THING TO CONFIRM WITH DEVANSH BEFORE INTEGRATION
--------------------------------------------------------
The project reference doc describes the ML output as a 3-way label
(SAFE / SOURCE_CODE / CONFIDENTIAL). What we actually trained is the
richer 9-category label (API_KEY, PASSWORD, EMAIL, PHONE,
PAYMENT_CARD, PII, SAFE, SOURCE_CODE, CONFIDENTIAL), since it's more
informative for the risk engine and the admin dashboard's "detected
categories" view. Both are available below — `classify()` returns
the fine-grained label by default, and `to_coarse()` collapses it to
the 3-way view if Devansh's risk engine was built expecting that
instead. Settle which one his code expects before wiring this in.
"""

import joblib
from pathlib import Path

_MODEL = None
MAX_CHARS = 100_000  # defensive cap; Devansh's validation should already enforce the 1MB file limit

MODEL_PATH = Path(__file__).resolve().parent.parent / "final_model.joblib"


def load_model(path: Path = MODEL_PATH) -> None:
    """Load the trained model into memory once. Call this at FastAPI startup,
    not on every request — reloading from disk per-request would blow the
    SRS's 2-second response budget for no reason."""
    global _MODEL
    _MODEL = joblib.load(path)


def classify(text: str) -> dict:
    """
    Classify submitted text into one of the 9 fine-grained labels.

    Returns: {"label": str, "confidence": float}

    Raises ValueError on empty input — Devansh's input validation should
    catch this before it ever reaches here, but we don't trust that
    blindly from inside this module.
    """
    if _MODEL is None:
        load_model()
    if not text or not text.strip():
        raise ValueError("classify() received empty text")

    probs = _MODEL.predict_proba([text[:MAX_CHARS]])[0]
    best_index = probs.argmax()
    return {
        "label": str(_MODEL.classes_[best_index]),
        "confidence": round(float(probs[best_index]), 4),
    }


def to_coarse(label: str) -> str:
    """Collapse a fine-grained label to the SRS's 3-way SAFE / SOURCE_CODE /
    CONFIDENTIAL view, in case Devansh's risk engine expects that instead."""
    if label in ("SAFE", "SOURCE_CODE", "CONFIDENTIAL"):
        return label
    return "CONFIDENTIAL"
