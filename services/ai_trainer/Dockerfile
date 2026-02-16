# Dockerfile for AI Trainer Service
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir \
    pandas \
    requests \
    torch \
    schedule

CMD ["python", "scheduler.py"]