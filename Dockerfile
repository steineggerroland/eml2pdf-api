# Slim Bookworm has good package availability for Pango/Cairo
FROM python:3.12-slim-bookworm

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "-u", "app.py"]
