FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project
COPY *.py dashboard.html ./

RUN useradd --system --uid 10001 relay && mkdir /data && chown relay /data
USER relay
ENV RELAY_DATABASE_URL=sqlite:////data/agent-relay.db

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
