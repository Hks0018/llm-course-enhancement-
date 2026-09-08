FROM python:3.11-slim

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY course_enhancer ./course_enhancer
COPY webapp ./webapp

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD uvicorn webapp.app:app --host 0.0.0.0 --port ${PORT:-8000}
