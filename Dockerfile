FROM python:3.11-slim

# Install system dependencies (Tesseract + poppler for pdf2image)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Start the app with increased timeout and single worker
CMD ["gunicorn", "--timeout", "120", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]