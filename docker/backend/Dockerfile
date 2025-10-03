FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src

# Install dependencies
RUN uv sync --frozen --no-cache

# Ensure the project package and console scripts (uvicorn, etc.) are installed
RUN python -m pip install --upgrade pip \
    && python -m pip install .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "nabr.main:app", "--host", "0.0.0.0", "--port", "8000"]
