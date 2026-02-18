FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by various packages
# - build-essential: compilation tools for Python C extensions
# - ffmpeg: audio processing for voice features (Day 4)
# - libpq-dev: PostgreSQL client library for psycopg2
# - libffi-dev: required by cryptography package
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for data persistence
RUN mkdir -p /app/data /app/uploads

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Expose API port
EXPOSE 8000

# Use entrypoint to run migrations before starting the app
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (overridden by docker-compose for development)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
