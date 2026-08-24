FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install the reviewed, fully resolved runtime dependency set.
COPY pyproject.toml LICENSE requirements.runtime.lock /app/
COPY apps/ /app/apps/
COPY data/ /app/data/
COPY profiles/ /app/profiles/
COPY scripts/ /app/scripts/
RUN pip install --no-cache-dir -r requirements.runtime.lock
RUN pip install --no-cache-dir --no-deps .
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/reports \
    && chown -R appuser:appuser /app/reports

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
