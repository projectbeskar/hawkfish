FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .

EXPOSE 8443

CMD ["python", "-m", "hawkfish_controller", "--host", "0.0.0.0", "--port", "8443"]


