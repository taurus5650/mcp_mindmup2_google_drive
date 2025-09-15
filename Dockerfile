FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install Poetry
RUN pip install poetry

# Configure poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only=main --no-root

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p deployment/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV ENV=production
ENV MCP_MODE=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=9801

# Expose port for HTTP server
EXPOSE 9801

# Default command runs the MCP server
CMD ["python", "main.py"]