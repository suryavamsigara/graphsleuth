FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY apps/ ./apps/
COPY engine/ ./engine/
COPY storage/ ./storage/

EXPOSE 8000

CMD ["uvicorn", "apps.api.app:app", "--host", "0.0.0.0", "--port", "8000"]