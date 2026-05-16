FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application + training data
COPY challenge/ ./challenge/
COPY data/ ./data/

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn challenge:app --host 0.0.0.0 --port ${PORT}"]
