# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim AS runtime
WORKDIR /app

# Non-root user - never run the app as root in production.
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY agent/ ./agent/

USER appuser

ENTRYPOINT ["python", "-m", "agent.cli"]
CMD ["What is 23 * 47 + 10?"]
