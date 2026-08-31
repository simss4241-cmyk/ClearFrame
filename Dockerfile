# CLEARFRAME — Screenplay Clearance Production Studio
# Base image: Python 3.11-slim
FROM python:3.11-slim

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system utilities & SSL certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application source code and seed fixtures
COPY backend /app/backend
COPY frontend /app/frontend
COPY seed /app/seed

# Expose port (Cloud Run dynamically sets $PORT)
EXPOSE 8080

# Launch FastAPI app with uvicorn
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
