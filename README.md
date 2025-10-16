## Agentic AI Compliance Officer

Stack: FastAPI (backend), Streamlit (frontend), LangChain + Gemini (reasoning)

### Setup
1) Create .env with `GEMINI_API_KEY=...`
2) Install deps: `pip install -r requirements.txt`
3) Run backend: `uvicorn backend.main:app --reload`
4) Run frontend: `streamlit run frontend/app.py`

Backend docs at /docs

### Endpoints
- POST /upload_regulation
- POST /check_compliance
- POST /generate_report
- GET /download_report/{report_id}

### Docker
```
docker build -t compliance-ai .
docker run -e GEMINI_API_KEY=$GEMINI_API_KEY -p 8000:8000 -p 8501:8501 compliance-ai
```


