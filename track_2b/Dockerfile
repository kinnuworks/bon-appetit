# Bon·Appétit app image. The language model is not inside this image: it is reached through
# LLM_BASE_URL (a judge's server, the bundled llama.cpp service, or a Swiss cloud endpoint).
# The Swiss embedding model and the precomputed FSVO vectors are baked in at build time,
# so search in the container is the same as in the evaluation and needs no network at runtime.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BONAPPETIT_EMBED=1 HF_HOME=/app/hf HF_HUB_OFFLINE=0 \
    BONAPPETIT_DATA=/app/data BONAPPETIT_SITE=/app/site BONAPPETIT_CACHE=/app/data/llm_cache.jsonl
WORKDIR /app
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir "sentence-transformers>=3.0,<4" pytest
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir')"
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY data/fsvo.csv data/fsvo_embeddings.npy data/llm_cache.jsonl ./data/
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/api/health')"
COPY eval ./eval
COPY tests ./tests
COPY site ./site
EXPOSE 8080
CMD ["uvicorn", "bonappetit.server:app", "--host", "0.0.0.0", "--port", "8080"]
