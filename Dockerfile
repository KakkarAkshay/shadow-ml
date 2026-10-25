FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=8000 \
    MODEL_PATH=final_model.joblib \
    APP_VERSION=dev

WORKDIR /app

RUN useradd --create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser ml/ ml/
COPY --chown=appuser:appuser static/ static/
COPY --chown=appuser:appuser final_model.joblib .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('APP_PORT', '8000'))"]

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}"]
