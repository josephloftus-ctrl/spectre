FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/backend/

# Create data directory
RUN mkdir -p /app/data/inbox /app/data/processed /app/data/embeddings

ENV PYTHONPATH=/app
ENV SPECTRE_DATA_DIR=/app/data
ENV SPECTRE_DB_PATH=/app/data/spectre.db

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
