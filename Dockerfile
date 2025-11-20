FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# instalar deps só a partir dos teus ficheiros
COPY api/requirements.txt api/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# copiar o código (única fonte = ./api/app)
COPY api/app ./app

EXPOSE 8000

# arranque
CMD ["python", "-m", "uvicorn", "app.main:app", "--host","0.0.0.0","--port","8000","--reload","--reload-dir","/app/app"]
