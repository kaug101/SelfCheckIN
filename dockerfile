# Start from slim Python image
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory inside container
WORKDIR /app

# Install system dependencies (optional: add more as needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies separately to enable caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your application (after dependencies installed)
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Launch app via gunicorn (faster than Flask dev server)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]
