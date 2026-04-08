FROM python:3.10-slim

# Prevent Python from buffering stdout/stderr (vital for Docker logs)
ENV PYTHONUNBUFFERED=1

# Install PostgreSQL client tools (needed for pg_isready in entrypoint.sh)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make the orchestrator executable
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]