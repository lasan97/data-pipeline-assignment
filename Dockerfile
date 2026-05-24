FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db ./db
COPY scripts ./scripts
COPY src ./src

EXPOSE 8050

CMD ["sh", "scripts/start.sh"]
