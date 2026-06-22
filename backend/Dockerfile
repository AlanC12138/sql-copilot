FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.1.0

COPY pyproject.toml ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
