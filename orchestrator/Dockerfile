# orchestrator/Dockerfile
FROM python:3.11-slim

# Install system deps for gTTS / ffmpeg (voice) & pandoc if you need conversions
RUN apt-get update && apt-get install -y \
    ffmpeg \
    pandoc \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose the port
EXPOSE 8000

# Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
