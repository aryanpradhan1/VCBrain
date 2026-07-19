FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the entire backend directory
COPY backend/ /app/backend/
COPY shared/ /app/shared/

# Create data directory for SQLite
RUN mkdir -p /app/backend/data

WORKDIR /app/backend/api

# Expose port
EXPOSE $PORT

# Start command
CMD python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
