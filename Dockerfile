FROM python:3.11-slim

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

ENV PYTHONPATH=/app

COPY pyproject.toml uv.lock ./

RUN uv venv --python=python3.11 \
 && uv pip install --upgrade pip \
 && uv sync

COPY . .

EXPOSE 8000

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
