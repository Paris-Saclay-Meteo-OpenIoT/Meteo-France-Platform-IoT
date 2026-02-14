FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create runtime directories
RUN mkdir -p /app/logs /app/frontend_output

# Copy application files
COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
