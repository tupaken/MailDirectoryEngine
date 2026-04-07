FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY llmService/ /app/llmService/
RUN pip install --upgrade pip && pip install /app/llmService

ENTRYPOINT ["python", "-m", "llmService.main"]
