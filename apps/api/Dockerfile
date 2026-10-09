FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/workspace/apps/api
WORKDIR /workspace
COPY apps/api/requirements.lock /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/api apps/api
COPY database database
COPY alembic.ini pyproject.toml ./
RUN mkdir -p data/uploads
CMD ["sh", "-c", "alembic upgrade head && uvicorn gaia.main:app --app-dir apps/api --host 0.0.0.0 --port 8000 --workers 1"]
