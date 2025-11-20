FROM python:3.11-slim
WORKDIR /workers
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["celery", "-A", "workers.app.celery_app", "worker", "--loglevel=INFO"]
