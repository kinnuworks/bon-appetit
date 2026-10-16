# Bon·Appétit app image. The language model is not inside this image: it is reached through
# LLM_BASE_URL (a judge's server, the bundled llama.cpp service, or a Swiss cloud endpoint).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BONAPPETIT_EMBED=0
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . pytest
COPY data/fsvo.csv data/llm_cache.jsonl ./data/
COPY eval ./eval
COPY tests ./tests
COPY site ./site
EXPOSE 8080
CMD ["uvicorn", "bonappetit.server:app", "--host", "0.0.0.0", "--port", "8080"]
