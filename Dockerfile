# Multi-stage build for HawkFish controller optimized for Kubernetes

# Build UI
FROM node:18-alpine AS ui-builder
WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm ci --only=production
COPY ui/ ./
RUN npm run build

# Python build stage
FROM python:3.11-slim as python-builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libvirt-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --user --no-cache-dir .[virt]

# Final runtime stage
FROM python:3.11-slim

# Add labels for Kubernetes and container registry
LABEL maintainer="HawkFish Team <maintainers@hawkfish.local>"
LABEL org.opencontainers.image.title="HawkFish Controller"
LABEL org.opencontainers.image.description="Cloud-native virtualization management platform with Redfish API"
LABEL org.opencontainers.image.vendor="HawkFish Project"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/projectbeskar/hawkfish"

# Build argument for version
ARG VERSION=dev
LABEL org.opencontainers.image.version="${VERSION}"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libvirt0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create hawkfish user with specific UID for Kubernetes compatibility
RUN groupadd -r hawkfish -g 1000 && useradd -r -g hawkfish -u 1000 -d /home/hawkfish hawkfish \
    && mkdir -p /home/hawkfish \
    && chown hawkfish:hawkfish /home/hawkfish

# Copy Python dependencies from builder
COPY --from=python-builder /root/.local /home/hawkfish/.local

# Copy application code
WORKDIR /app
COPY src/ ./src/
COPY pyproject.toml ./

# Copy UI build from ui-builder
COPY --from=ui-builder /app/ui/dist ./ui/dist

# Create state directories with proper permissions
RUN mkdir -p /var/lib/hawkfish/data \
             /var/lib/hawkfish/isos \
             /var/lib/hawkfish/logs \
             /tmp/hawkfish \
    && chown -R hawkfish:hawkfish /var/lib/hawkfish /tmp/hawkfish

# Set up PATH and Python environment
ENV PATH="/home/hawkfish/.local/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Kubernetes-optimized configuration
ENV HF_HOST=0.0.0.0
ENV HF_PORT=8080
ENV HF_DATA_DIR=/var/lib/hawkfish/data
ENV HF_ISO_PATH=/var/lib/hawkfish/isos
ENV HF_LOG_LEVEL=INFO
ENV HF_AUTH_REQUIRED=true
ENV HF_UI_ENABLED=true
ENV HF_METRICS_ENABLED=true
ENV HF_WORKER_COUNT=4

# Health check optimized for Kubernetes
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${HF_PORT}/redfish/v1/ || exit 1

# Switch to non-root user
USER hawkfish

# Expose port
EXPOSE 8080

# Add version information
RUN echo "${VERSION}" > /app/VERSION

# Run the application with proper signal handling for Kubernetes
CMD ["python", "-m", "hawkfish_controller"]
