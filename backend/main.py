"""
FastAPI Backend for Agentic AI Compliance Officer
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import os
import logging

from .models import ComplianceCheck, ComplianceReport, RegulationDocument
from .compliance_agent import ComplianceAgent
from .report_utils import ReportGenerator
from dotenv import load_dotenv
from .db import init_db, get_session, engine
from .schemas import Regulation as RegulationRow, ComplianceCheckRow, ReportRow, Source, SourceVersion
from sqlmodel import Session, select
from apscheduler.schedulers.background import BackgroundScheduler
import httpx
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compliance_api")

app = FastAPI(
    title="Agentic AI Compliance Officer API",
    description="AI-powered compliance monitoring and reporting system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Load environment variables from .env if present
load_dotenv()
init_db()
# Disable background scheduler on serverless runtimes
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
scheduler = None
if not IS_SERVERLESS:
    scheduler = BackgroundScheduler()
    scheduler.start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy init agent; fail fast if missing key
agent = None
try:
    agent = ComplianceAgent()
except Exception as e:
    logger.warning(f"ComplianceAgent not initialized: {e}")
reporter = ReportGenerator()

# Legacy in-memory stores (kept for backward compatibility if needed)
regulations_db: Dict[str, Dict[str, Any]] = {}
compliance_checks_db: Dict[str, Dict[str, Any]] = {}
reports_db: Dict[str, Dict[str, Any]] = {}


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@app.get("/", response_model=APIResponse)
async def health():
    return APIResponse(
        success=True,
        message="OK",
        data={
            "timestamp": datetime.utcnow().isoformat(),
            "serverless": IS_SERVERLESS,
            "agent_ready": agent is not None,
        },
    )


@app.post("/upload_regulation", response_model=APIResponse)
async def upload_regulation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    regulation_type: str = "general",
    jurisdiction: str = "global",
    effective_date: Optional[str] = None,
):
    try:
        allowed = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        }
        if file.content_type not in allowed:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        os.makedirs("temp_uploads", exist_ok=True)
        regulation_id = str(uuid.uuid4())
        temp_path = os.path.join("temp_uploads", f"{regulation_id}_{file.filename}")
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        background_tasks.add_task(
            _process_regulation_document,
            regulation_id,
            temp_path,
            file.filename,
            regulation_type,
            jurisdiction,
            effective_date,
        )

        return APIResponse(
            success=True,
            message="File received. Processing in background.",
            data={"regulation_id": regulation_id, "status": "processing"},
        )
    except Exception as e:
        logger.exception("upload_regulation failed")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_regulation_document(
    regulation_id: str,
    file_path: str,
    filename: str,
    regulation_type: str,
    jurisdiction: str,
    effective_date: Optional[str],
):
    try:
        extracted_text = await agent.extract_document_text(file_path)
        analysis = await agent.analyze_regulation(extracted_text, regulation_type, jurisdiction)

        doc = RegulationDocument(
            id=regulation_id,
            filename=filename,
            file_path=file_path,
            regulation_type=regulation_type,
            jurisdiction=jurisdiction,
            effective_date=effective_date,
            extracted_text=extracted_text,
            analysis_result=analysis,
            upload_date=datetime.utcnow().isoformat(),
            status="processed",
        )
        # Persist to DB using a direct session on the engine
        with Session(engine) as session:
            row = RegulationRow(
                id=doc.id,
                filename=doc.filename,
                file_path=doc.file_path,
                regulation_type=doc.regulation_type,
                jurisdiction=doc.jurisdiction,
                effective_date=doc.effective_date,
                extracted_text=doc.extracted_text,
                analysis_result=doc.analysis_result,
                upload_date=doc.upload_date,
                status=doc.status,
            )
            session.add(row)
            session.commit()
        regulations_db[regulation_id] = doc.model_dump()
    except Exception as e:
        regulations_db[regulation_id] = {
            "id": regulation_id,
            "filename": filename,
            "status": "error",
            "error": str(e),
        }
        logger.exception("process_regulation_document failed")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@app.post("/check_compliance", response_model=APIResponse)
async def check_compliance(payload: ComplianceCheck, session: Session = Depends(get_session)):
    try:
        # Prefer DB
        db_reg = session.exec(select(RegulationRow).where(RegulationRow.id == payload.regulation_id)).first()
        if db_reg:
            reg = {
                "extracted_text": db_reg.extracted_text,
                "analysis_result": db_reg.analysis_result,
                "status": db_reg.status,
            }
        else:
            reg = regulations_db.get(payload.regulation_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Regulation not found")
        if reg.get("status") != "processed":
            raise HTTPException(status_code=400, detail="Regulation not processed yet")

        result = await agent.check_compliance(
            regulation_text=reg["extracted_text"],
            company_policies=payload.company_policies,
            regulation_analysis=reg["analysis_result"],
        )

        check_id = str(uuid.uuid4())
        # Persist
        session.add(ComplianceCheckRow(id=check_id, regulation_id=payload.regulation_id, result=result))
        session.commit()
        compliance_checks_db[check_id] = {
            "id": check_id,
            "regulation_id": payload.regulation_id,
            "result": result,
            "created_at": datetime.utcnow().isoformat(),
        }

        return APIResponse(
            success=True,
            message="Compliance check complete",
            data={"check_id": check_id, **result},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("check_compliance failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_report", response_model=APIResponse)
async def generate_report(payload: ComplianceReport, format: str = "pdf", session: Session = Depends(get_session)):
    try:
        # Prefer DB for regulation
        db_reg = session.exec(select(RegulationRow).where(RegulationRow.id == payload.regulation_id)).first()
        if db_reg:
            reg = db_reg.__dict__
        else:
            reg = regulations_db.get(payload.regulation_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Regulation not found")
        # Collect checks from DB
        db_checks = session.exec(select(ComplianceCheckRow).where(ComplianceCheckRow.regulation_id == payload.regulation_id)).all()
        relevant_checks: List[Dict[str, Any]] = []
        for c in db_checks:
            relevant_checks.append({"id": c.id, "regulation_id": c.regulation_id, "compliance_result": c.result, "check_date": c.created_at, "status": "completed"})
        # Also merge legacy in-memory
        legacy_checks = [v for v in compliance_checks_db.values() if v["regulation_id"] == payload.regulation_id]
        relevant_checks.extend(legacy_checks)

        path = await reporter.generate_report(
            regulation_data=reg,
            compliance_checks=relevant_checks,
            report_format=format,
            include_recommendations=payload.include_recommendations,
        )
        report_id = str(uuid.uuid4())
        session.add(ReportRow(id=report_id, regulation_id=payload.regulation_id, format=format, file_path=path))
        session.commit()
        reports_db[report_id] = {
            "id": report_id,
            "regulation_id": payload.regulation_id,
            "format": format,
            "file_path": path,
            "created_at": datetime.utcnow().isoformat(),
        }
        return APIResponse(success=True, message="Report generated", data={"report_id": report_id, "file_path": path})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("generate_report failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download_report/{report_id}")
async def download_report(report_id: str, session: Session = Depends(get_session)):
    meta = reports_db.get(report_id)
    if not meta:
        row = session.get(ReportRow, report_id)
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        meta = {"file_path": row.file_path, "format": row.format}
    if not os.path.exists(meta["file_path"]):
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "application/pdf" if meta["format"] == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = f"compliance_report_{report_id}.{meta['format']}"
    return FileResponse(meta["file_path"], media_type=media_type, filename=filename)


# ✅ NEW ENDPOINT for Streamlit (/report/{regulation_id})
@app.get("/report/{regulation_id}")
async def get_report(regulation_id: str, format: str = "pdf", session: Session = Depends(get_session)):
    """
    Shortcut endpoint so frontend can call /report/{regulation_id}?format=pdf
    without needing to separately call generate + download.
    """
    # 1. Check if a report already exists
    db_reports = session.exec(select(ReportRow).where(ReportRow.regulation_id == regulation_id)).all()
    if db_reports:
        latest = db_reports[-1]
        if os.path.exists(latest.file_path):
            media_type = "application/pdf" if latest.format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"compliance_report_{regulation_id}.{latest.format}"
            return FileResponse(latest.file_path, media_type=media_type, filename=filename)

    # 2. Auto-generate if missing
    payload = ComplianceReport(regulation_id=regulation_id, include_recommendations=True)
    path = await reporter.generate_report(
        regulation_data=regulations_db.get(regulation_id) or {},
        compliance_checks=[c for c in compliance_checks_db.values() if c["regulation_id"] == regulation_id],
        report_format=format,
        include_recommendations=True,
    )
    return FileResponse(path, media_type="application/pdf", filename=f"compliance_report_{regulation_id}.pdf")


@app.get("/regulations", response_model=APIResponse)
async def list_regulations(session: Session = Depends(get_session)):
    db_items = session.exec(select(RegulationRow)).all()
    items = [
        {
            "id": r.id,
            "filename": r.filename,
            "file_path": r.file_path,
            "regulation_type": r.regulation_type,
            "jurisdiction": r.jurisdiction,
            "effective_date": r.effective_date,
            "extracted_text": r.extracted_text,
            "analysis_result": r.analysis_result,
            "upload_date": r.upload_date,
            "status": r.status,
        }
        for r in db_items
    ]
    items.extend(list(regulations_db.values()))
    return APIResponse(success=True, message="OK", data={"items": items, "count": len(items)})


@app.get("/compliance_checks", response_model=APIResponse)
async def list_checks(session: Session = Depends(get_session)):
    db_items = session.exec(select(ComplianceCheckRow)).all()
    items = [
        {"id": c.id, "regulation_id": c.regulation_id, "result": c.result, "created_at": c.created_at}
        for c in db_items
    ]
    items.extend(list(compliance_checks_db.values()))
    return APIResponse(success=True, message="OK", data={"items": items, "count": len(items)})


@app.get("/reports", response_model=APIResponse)
async def list_reports(session: Session = Depends(get_session)):
    db_items = session.exec(select(ReportRow)).all()
    items = [
        {"id": r.id, "regulation_id": r.regulation_id, "format": r.format, "file_path": r.file_path, "created_at": r.created_at}
        for r in db_items
    ]
    items.extend(list(reports_db.values()))
    return APIResponse(success=True, message="OK", data={"items": items, "count": len(items)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# New: Professional report endpoint returning PDF directly
@app.post("/generate_professional_report")
async def generate_professional_report(payload: ComplianceReport, session: Session = Depends(get_session)):
    try:
        # Fetch regulation
        db_reg = session.exec(select(RegulationRow).where(RegulationRow.id == payload.regulation_id)).first()
        if db_reg:
            reg = db_reg.__dict__
        else:
            reg = regulations_db.get(payload.regulation_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Regulation not found")

        # Gather compliance checks
        db_checks = session.exec(select(ComplianceCheckRow).where(ComplianceCheckRow.regulation_id == payload.regulation_id)).all()
        relevant_checks = [
            {"id": c.id, "regulation_id": c.regulation_id, "result": c.result, "created_at": c.created_at}
            for c in db_checks
        ]
        # Add legacy checks if any
        legacy_checks = [v for v in compliance_checks_db.values() if v["regulation_id"] == payload.regulation_id]
        for v in legacy_checks:
            relevant_checks.append({"id": v["id"], "regulation_id": v["regulation_id"], "result": v.get("result") or v.get("compliance_result"), "created_at": v.get("created_at") or v.get("check_date")})

        # Generate PDF
        pdf_path = await reporter.generate_report(
            regulation_data=reg,
            compliance_checks=relevant_checks,
            report_format="pdf",
            include_recommendations=payload.include_recommendations,
        )

        # Persist report row
        report_id = str(uuid.uuid4())
        session.add(ReportRow(id=report_id, regulation_id=payload.regulation_id, format="pdf", file_path=pdf_path))
        session.commit()

        return FileResponse(pdf_path, media_type="application/pdf", filename=f"compliance_report_{report_id}.pdf")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("generate_professional_report failed")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Monitoring: sources and polling
# -----------------------------

@app.post("/monitor/sources", response_model=APIResponse)
async def add_source(name: str, url: str, jurisdiction: str = "global", regulation_type: str = "general", due_days: int | None = None, session: Session = Depends(get_session)):
    sid = str(uuid.uuid4())
    src = Source(id=sid, name=name, url=url, jurisdiction=jurisdiction, regulation_type=regulation_type, enabled=True, due_days=due_days)
    session.add(src)
    session.commit()
    return APIResponse(success=True, message="Source added", data={"id": sid})


@app.get("/monitor/sources", response_model=APIResponse)
async def list_sources(session: Session = Depends(get_session)):
    rows = session.exec(select(Source)).all()
    data = [{"id": r.id, "name": r.name, "url": r.url, "enabled": r.enabled, "jurisdiction": r.jurisdiction, "regulation_type": r.regulation_type, "due_days": r.due_days} for r in rows]
    return APIResponse(success=True, message="OK", data={"items": data, "count": len(data)})


async def fetch_and_check_source(session: Session, src: Source):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(src.url)
            resp.raise_for_status()
            content = resp.text
        h = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
        last = session.exec(select(SourceVersion).where(SourceVersion.source_id == src.id).order_by(SourceVersion.fetched_at.desc())).first()
        if last and last.hash == h:
            return False  # no change
        # store version
        ver = SourceVersion(id=str(uuid.uuid4()), source_id=src.id, hash=h, title=None, snippet=content[:200])
        session.add(ver)
        session.commit()

        # auto-create regulation entry for diff (simple: store as txt)
        reg_id = str(uuid.uuid4())
        extracted_text = content[:10000]
        analysis = await agent.analyze_regulation(extracted_text, src.regulation_type, src.jurisdiction)
        doc = RegulationDocument(
            id=reg_id,
            filename=f"monitor_{src.name}.txt",
            file_path="",
            regulation_type=src.regulation_type,
            jurisdiction=src.jurisdiction,
            effective_date=None,
            extracted_text=extracted_text,
            analysis_result=analysis,
            upload_date=datetime.utcnow().isoformat(),
            status="processed",
        )
        session.add(RegulationRow(**doc.model_dump()))
        session.commit()
        return True
    except Exception:
        logger.exception("fetch_and_check_source failed")
        return False


@app.post("/monitor/run", response_model=APIResponse)
async def run_monitor(session: Session = Depends(get_session)):
    rows = session.exec(select(Source).where(Source.enabled == True)).all()
    changes = 0
    for r in rows:
        changed = await fetch_and_check_source(session, r)
        if changed:
            changes += 1
    return APIResponse(success=True, message="Monitor completed", data={"changes": changes, "checked": len(rows)})


def schedule_job():
    with Session(engine) as s:
        rows = s.exec(select(Source).where(Source.enabled == True)).all()
    # This is a lightweight trigger; detailed polling handled in endpoint for demo
    logger.info(f"Scheduled monitor tick. {len(rows)} sources configured")


if scheduler is not None:
    scheduler.add_job(
        schedule_job,
        "interval",
        minutes=30,
        id="monitor_tick",
        replace_existing=True,
    )
