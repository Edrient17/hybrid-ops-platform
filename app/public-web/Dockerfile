FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV SERVICE_NAME=public-web-app
ENV APP_VERSION=v0.1.0
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]