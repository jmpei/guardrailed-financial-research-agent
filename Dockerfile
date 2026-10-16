# The demo (app.py) on CPU; the agent calls OpenAI, so pass OPENAI_API_KEY at run time:
#   docker build -t gfra .
#   docker run -p 8080:8080 -e OPENAI_API_KEY gfra
# data/index and the filing PDFs are gitignored, so build from a checkout that has them (see .dockerignore).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /usr/local/bin/uv
# git: Progent is a git dependency.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# app.py loads src/ from the checkout, so only the dependencies are installed.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app.py ./
COPY src ./src
COPY data ./data

RUN useradd --create-home app
USER app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=8080
EXPOSE 8080
CMD ["python", "app.py"]
