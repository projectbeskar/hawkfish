# Multi-stage build for HawkFish controller

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

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libvirt0 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create hawkfish user
RUN groupadd -r hawkfish && useradd -r -g hawkfish -u 1000 hawkfish

# Copy Python dependencies from builder
COPY --from=python-builder /root/.local /home/hawkfish/.local

# Copy application code
WORKDIR /app
COPY src/ ./src/
COPY pyproject.toml ./

# Copy UI build from ui-builder
COPY --from=ui-builder /app/ui/dist ./ui/dist

# Create state directories
RUN mkdir -p /var/lib/hawkfish/isos \
    && chown -R hawkfish:hawkfish /var/lib/hawkfish

# Create tmp directory for writable filesystem
RUN mkdir -p /tmp/hawkfish \
    && chown -R hawkfish:hawkfish /tmp/hawkfish

# Set up PATH
ENV PATH="/home/hawkfish/.local/bin:$PATH"
ENV PYTHONPATH="/app"

# Default configuration
ENV HF_API_HOST=0.0.0.0
ENV HF_API_PORT=8080
ENV HF_STATE_DIR=/var/lib/hawkfish
ENV HF_ISO_DIR=/var/lib/hawkfish/isos
ENV HF_AUTH=sessions
ENV HF_UI_ENABLED=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${HF_API_PORT}/redfish/v1/ || exit 1

# Switch to non-root user
USER hawkfish

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "hawkfish_controller"]
