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

# Create data directory
RUN mkdir -p /app/data

# Ensure the project package and console scripts are available in the image
RUN python -m pip install --upgrade pip \
    && python -m pip install .

CMD ["uv", "run", "python", "-m", "nabr.temporal.worker"]
