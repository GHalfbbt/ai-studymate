FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by various packages
# - build-essential: compilation tools for Python C extensions
# - ffmpeg: audio processing for voice features
# - libpq-dev: PostgreSQL client library for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for data persistence
RUN mkdir -p /app/data /app/uploads

# Expose API port
EXPOSE 8000

# Default command (overridden by docker-compose for development)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
