# Base image
FROM python:3.13-slim

# Workdir
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Environment
ENV FLASK_APP=app_v2_secure.py \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose
EXPOSE 5000

# Command
CMD ["python", "app_v2_secure.py"]
