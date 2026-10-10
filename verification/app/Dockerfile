# Restricted Disposable Lab Container for SENTINEL-X Verification (Layer 5)
FROM python:3.11-slim

# Install git for patch application and patch verification
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    patch \
    && rm -rf /var/lib/apt/lists/*

# Install test dependencies
RUN pip install --no-cache-dir pytest

# Create restricted sandbox workspace
WORKDIR /workspace

# Set Python path to find verification and app modules
ENV PYTHONPATH=/workspace:/workspace/app

# Default command: run immutable test suite
CMD ["pytest", "/workspace/verification/tests_suite", "-v"]
