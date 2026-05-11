FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies for PyMuPDF and faiss-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    libomp-dev \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Fix line endings (Windows -> Unix) and make entrypoint executable
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

# Expose the application port
EXPOSE 8000

# Run migrations then start the FastAPI app
ENTRYPOINT ["./entrypoint.sh"]
