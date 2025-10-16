FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GEMINI_API_KEY=""

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

EXPOSE 8000 8501

CMD bash -lc "\
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 & \
  streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 \" 


