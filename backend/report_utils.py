"""
Report generation utilities (PDF/Excel)
"""

from typing import Dict, Any, List
from datetime import datetime
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import xlsxwriter


class ReportGenerator:
    async def generate_report(
        self,
        regulation_data: Dict[str, Any],
        compliance_checks: List[Dict[str, Any]],
        report_format: str = "pdf",
        include_recommendations: bool = True,
    ) -> str:
        # In serverless (e.g., Vercel) write to /tmp
        out_dir = "/tmp/reports" if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "reports"
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        reg_id = regulation_data.get("id") or "unknown"
        base_name = f"report_{reg_id}_{ts}"
        if report_format == "pdf":
            path = os.path.join(out_dir, base_name + ".pdf")
            self._build_pdf(path, regulation_data, compliance_checks, include_recommendations)
            return path
        if report_format == "xlsx":
            path = os.path.join(out_dir, base_name + ".xlsx")
            self._build_xlsx(path, regulation_data, compliance_checks)
            return path
        raise ValueError("Unsupported format. Use 'pdf' or 'xlsx'.")

    def _build_pdf(self, path: str, reg: Dict[str, Any], checks: List[Dict[str, Any]], include_recs: bool) -> None:
        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 2 * cm

        def line(text: str, step: float = 14):
            nonlocal y
            c.drawString(2 * cm, y, text[:110])
            y -= step

        c.setFont("Helvetica-Bold", 16)
        line("Compliance Report")
        c.setFont("Helvetica", 10)
        line(f"Generated: {datetime.utcnow().isoformat()}Z")
        line("")

        c.setFont("Helvetica-Bold", 12)
        line("Regulation")
        c.setFont("Helvetica", 10)
        line(f"ID: {reg.get('id')}")
        line(f"Filename: {reg.get('filename')}")
        line(f"Type: {reg.get('regulation_type')} | Jurisdiction: {reg.get('jurisdiction')}")
        line("")

        analysis = reg.get("analysis_result", {})
        c.setFont("Helvetica-Bold", 12)
        line("Executive Summary")
        c.setFont("Helvetica", 10)
        for para in str(analysis.get("regulation_summary", "N/A")).split("\n"):
            line(para)
        line("")

        # Document Overview (personalized to input document)
        c.setFont("Helvetica-Bold", 12)
        line("Document Overview")
        c.setFont("Helvetica", 10)
        
        # Show document overview if available
        doc_overview = analysis.get("document_overview")
        if doc_overview:
            line(f"Overview: {doc_overview}")
        
        det_framework = analysis.get("detected_framework") or analysis.get("framework")
        if det_framework:
            line(f"Detected Framework: {det_framework}")
        key_reqs = analysis.get("key_requirements") or []
        if key_reqs:
            line("Key Requirements:")
            for kr in key_reqs[:8]:
                desc = kr.get("description") if isinstance(kr, dict) else str(kr)
                line(f"- {desc}")
        obligations = analysis.get("compliance_obligations") or []
        if obligations:
            line("Primary Obligations:")
            for ob in obligations[:6]:
                line(f"- {ob}")
        line("")

        c.setFont("Helvetica-Bold", 12)
        line("Compliance Checks")
        c.setFont("Helvetica", 10)
        overall_best_score = None
        last_detailed = None
        for chk in checks:
            result = chk.get("result") or chk.get("compliance_result") or {}
            result = chk.get("result") or chk.get("compliance_result") or {}
            score = result.get("compliance_score", "N/A")
            status = result.get("overall_status", "N/A")
            line(f"Check: {chk.get('id')} | Score: {score}")
            line(f"Status: {status}")
            if isinstance(score, (int, float)):
                overall_best_score = max(overall_best_score or 0, score)
            if result.get("detailed_analysis"):
                last_detailed = result.get("detailed_analysis")
            gaps = result.get("gaps", [])
            if gaps:
                line("Gaps:")
                for g in gaps[:10]:
                    line(f"- {g.get('requirement', 'N/A')}: {g.get('gap_description', '')}")
        line("")

        # Score bar visualization (simple)
        if overall_best_score is not None:
            c.setFont("Helvetica-Bold", 12)
            line("Compliance Score (Best)")
            c.setFont("Helvetica", 10)
            bar_x = 2 * cm
            bar_y = y
            bar_w = width - 4 * cm
            bar_h = 10
            # outline
            c.rect(bar_x, bar_y, bar_w, bar_h, stroke=1, fill=0)
            # fill proportional
            filled_w = max(0, min(100, int(overall_best_score))) / 100 * bar_w
            c.setFillGray(0.2)
            c.rect(bar_x, bar_y, filled_w, bar_h, stroke=0, fill=1)
            c.setFillGray(0.0)
            y -= 20
            line(f"Score: {int(overall_best_score)} / 100")
            line("")

        # Detected framework and sections (if provided by model)
        if last_detailed and isinstance(last_detailed, dict):
            framework = last_detailed.get("detected_framework")
            if framework:
                c.setFont("Helvetica-Bold", 12)
                line(f"Detected Framework: {framework}")
                c.setFont("Helvetica", 10)
                line("")

            sections = last_detailed.get("sections") or []
            if sections:
                c.setFont("Helvetica-Bold", 12)
                line("Sections Overview")
                c.setFont("Helvetica", 10)
                for s in sections[:12]:
                    s_name = s.get("name", "Section")
                    s_status = s.get("status", "N/A")
                    s_score = s.get("score", "N/A")
                    line(f"- {s_name} | Status: {s_status} | Score: {s_score}")
                line("")

        if include_recs:
            c.setFont("Helvetica-Bold", 12)
            line("Recommendations")
            c.setFont("Helvetica", 10)
            recs: List[str] = []
            
            # Collect recommendations from all sources
            for chk in checks:
                result = chk.get("result") or chk.get("compliance_result") or {}
                recs.extend(result.get("recommendations", []))
                
                # Also collect from detailed analysis
                detailed = result.get("detailed_analysis", {})
                if isinstance(detailed, dict):
                    recs.extend(detailed.get("top_recommendations", []))
                    for section in detailed.get("sections", []):
                        for gap in section.get("gaps", []):
                            recs.extend(gap.get("recommendations", []))
            
            # Also collect from regulation analysis
            reg_recs = analysis.get("recommended_actions", [])
            if reg_recs:
                recs.extend(reg_recs)
            
            # De-duplicate while preserving order
            seen = set()
            unique_recs = []
            for r in recs:
                if r and r not in seen and isinstance(r, str) and r.strip():
                    seen.add(r.strip())
                    unique_recs.append(r.strip())
            
            if unique_recs:
                for r in unique_recs[:20]:
                    line(f"- {r}")
            else:
                line("No specific recommendations available at this time.")

        # Tailored Suggestions per Document (derive additional suggestions from detailed sections)
        extra_suggestions: List[str] = []
        if last_detailed and isinstance(last_detailed, dict):
            for s in (last_detailed.get("sections") or [])[:10]:
                for g in s.get("gaps", [])[:3]:
                    for rcmd in g.get("recommendations", [])[:2]:
                        if rcmd and rcmd not in extra_suggestions:
                            extra_suggestions.append(rcmd)
        # If we have extra, print them on a new page block
        if extra_suggestions:
            line("")
            c.setFont("Helvetica-Bold", 12)
            line("Tailored Suggestions (From this Document)")
            c.setFont("Helvetica", 10)
            for r in extra_suggestions[:15]:
                line(f"- {r}")

        c.showPage()
        c.save()

    def _build_xlsx(self, path: str, reg: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
        workbook = xlsxwriter.Workbook(path)
        try:
            # Sheet: Regulation
            ws_meta = workbook.add_worksheet("Regulation")
            headers = ["field", "value"]
            for col, h in enumerate(headers):
                ws_meta.write(0, col, h)
            meta_rows = [
                ("id", reg.get("id")),
                ("filename", reg.get("filename")),
                ("type", reg.get("regulation_type")),
                ("jurisdiction", reg.get("jurisdiction")),
                ("uploaded", reg.get("upload_date")),
            ]
            for r, (k, v) in enumerate(meta_rows, start=1):
                ws_meta.write(r, 0, k)
                ws_meta.write(r, 1, v)

            # Sheet: Checks
            ws_checks = workbook.add_worksheet("Checks")
            checks_headers = ["check_id", "score", "status"]
            for col, h in enumerate(checks_headers):
                ws_checks.write(0, col, h)
            row_idx = 1
            for chk in checks:
                res = chk.get("result") or chk.get("compliance_result") or {}
                ws_checks.write(row_idx, 0, chk.get("id"))
                ws_checks.write(row_idx, 1, res.get("compliance_score"))
                ws_checks.write(row_idx, 2, res.get("overall_status"))
                row_idx += 1

            # Sheet: Gaps
            ws_gaps = workbook.add_worksheet("Gaps")
            gaps_headers = ["check_id", "requirement", "gap", "impact", "effort"]
            for col, h in enumerate(gaps_headers):
                ws_gaps.write(0, col, h)
            row_idx = 1
            for chk in checks:
                res = chk.get("result") or chk.get("compliance_result") or {}
                for g in res.get("gaps", []):
                    ws_gaps.write(row_idx, 0, chk.get("id"))
                    ws_gaps.write(row_idx, 1, g.get("requirement"))
                    ws_gaps.write(row_idx, 2, g.get("gap_description"))
                    ws_gaps.write(row_idx, 3, g.get("impact_level"))
                    ws_gaps.write(row_idx, 4, g.get("remediation_effort"))
                    row_idx += 1
        finally:
            workbook.close()



