FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY llmService/ /app/llmService/
RUN pip install --upgrade pip && pip install \
    "beautifulsoup4>=4.14.3" \
    "dotenv>=0.9.9" \
    "ollama>=0.6.1" \
    "psycopg[binary]>=3.3.3" \
    "sqlalchemy>=2.0.48"

ENTRYPOINT ["python", "-m", "llmService.main"]
