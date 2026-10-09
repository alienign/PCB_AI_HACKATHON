FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu \
       'torch==2.14.1+cpu' 'torchvision==0.29.1+cpu' \
    && python -m pip install -r requirements.txt \
    && python -m pip uninstall -y opencv-python opencv-contrib-python \
    && python -m pip install opencv-python-headless

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY scripts/preflight.py ./scripts/preflight.py

RUN mkdir -p /app/storage /app/models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
