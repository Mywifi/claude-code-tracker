FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY . .

# Install dependencies
RUN uv pip install --system .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8082

# Environment variables
ENV PORT=8082
ENV DATA_DIR=/app/data

# Run the proxy
CMD ["claude-tracker"]
