# Restricted Disposable Lab Environment for SENTINEL-X Verification (Layer 5)
FROM python:3.11-slim

# Install system dependencies for patch application
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    patch \
    && rm -rf /var/lib/apt/lists/*

# Install Pytest
RUN pip install --no-cache-dir pytest

# Create restricted workspace
WORKDIR /workspace

# Python path
ENV PYTHONPATH=/workspace

# Default command
CMD ["pytest", "/workspace/verification/protected_tests", "-v"]
