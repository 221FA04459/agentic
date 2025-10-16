"""
LangChain + Gemini compliance agent
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
try:
    import pdfplumber  # optional, may be omitted in serverless
except Exception:  # pragma: no cover
    pdfplumber = None
import PyPDF2
import docx
logger = logging.getLogger(__name__)


class ComplianceAgent:
    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")

        # Use direct Google Generative AI instead of LangChain to avoid version conflicts
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")

    async def extract_document_text(self, file_path: str) -> str:
        ext = file_path.lower().split(".")[-1]
        if ext == "pdf":
            # Prefer pdfplumber if available; otherwise fall back to PyPDF2
            if pdfplumber is not None:
                try:
                    text = ""
                    with pdfplumber.open(file_path) as pdf:
                        for p in pdf.pages:
                            t = p.extract_text() or ""
                            if t:
                                text += t + "\n"
                    if text.strip():
                        return text.strip()
                except Exception:
                    pass
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join([p.extract_text() or "" for p in reader.pages]).strip()
        if ext in {"doc", "docx"}:
            d = docx.Document(file_path)
            return "\n".join([p.text for p in d.paragraphs]).strip()
        if ext == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        raise ValueError(f"Unsupported file type: {ext}")

    async def analyze_regulation(self, text: str, regulation_type: str, jurisdiction: str) -> Dict[str, Any]:
        # Feed more context to improve document-specific outputs
        if len(text) > 15000:
            text = text[:15000]

        prompt = (
            "You are an AI Compliance Officer.\n\n"
            "Objective: Analyze the provided regulatory content and summarize obligations.\n"
            "Rules: Output STRICT JSON only. If unknown, use null or [].\n\n"
            f"Hints -> regulation_type: {regulation_type}, jurisdiction: {jurisdiction}\n"
            "Source Text (truncated):\n" + text + "\n\n"
            "JSON Schema: {\n"
            "  \"regulation_summary\": \"string\",\n"
            "  \"key_requirements\": [{\n"
            "    \"id\": \"string\", \"description\": \"string\", \"category\": \"string\", \"priority\": \"high|medium|low\"\n"
            "  }],\n"
            "  \"compliance_obligations\": [\"string\"],\n"
            "  \"risk_assessment\": {\"overall_risk\": \"high|medium|low\"},\n"
            "  \"implementation_timeline\": \"string|null\",\n"
            "  \"affected_departments\": [\"string\"],\n"
            "  \"penalties_and_enforcement\": \"string|null\",\n"
            "  \"recommended_actions\": [\"string\"],\n"
            "  \"detected_framework\": \"string\",\n"
            "  \"document_overview\": \"string\"\n"
            "}\n"
            "Return only JSON."
        )

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            raw = (response.text or "").strip()
            try:
                return json.loads(raw)
            except Exception:
                # Fallback to minimal structure using raw text
                return {
                    "regulation_summary": raw[:500] + ("..." if len(raw) > 500 else ""),
                    "key_requirements": [],
                    "compliance_obligations": [],
                    "risk_assessment": {"overall_risk": "medium"},
                    "implementation_timeline": None,
                    "affected_departments": [],
                    "penalties_and_enforcement": None,
                    "recommended_actions": [],
                    "detected_framework": regulation_type,
                    "document_overview": f"Document analysis for {regulation_type} regulation in {jurisdiction}",
                }
        except Exception as e:
            logger.error(f"Error in analyze_regulation: {str(e)}")
            return {
                "regulation_summary": f"Analysis generated for {regulation_type} ({jurisdiction})",
                "key_requirements": [],
                "compliance_obligations": [],
                "risk_assessment": {"overall_risk": "medium"},
                "implementation_timeline": None,
                "affected_departments": [],
                "penalties_and_enforcement": None,
                "recommended_actions": [],
                "detected_framework": regulation_type,
                "document_overview": f"Document analysis for {regulation_type} regulation in {jurisdiction}",
            }

    async def check_compliance(self, regulation_text: str, company_policies: List[str], regulation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        policies_text = "\n".join(company_policies) if company_policies else "No specific policies provided"
        # Feed more of the source for better grounding
        truncated = regulation_text[:6000]
        
        # Prepare hint values safely
        hint_type = (
            regulation_analysis.get("detected_framework")
            or regulation_analysis.get("regulation_type")
            or "general"
        )
        hint_jurisdiction = regulation_analysis.get("jurisdiction") or "unknown"

        # Universal, regulation-detecting JSON-only prompt
        prompt = (
            "You are an AI Compliance Officer.\n\n"
            "Objective: Analyze the provided regulatory content and produce a structured compliance assessment specific to the detected framework.\n"
            "Rules: Output STRICT JSON only (no markdown). Status in {compliant, partially_compliant, non_compliant}. Scores are 0-100 integers.\n"
            "Do not invent facts; if unknown use null or []. Recommendations must be concrete and actionable.\n\n"
            f"Hints -> regulation_type: {hint_type}, jurisdiction: {hint_jurisdiction}\n"
            "Company Policies:\n" + policies_text + "\n\n"
            "Source Text (truncated):\n" + truncated + "\n\n"
            "IMPORTANT: Generate specific, actionable recommendations based ONLY on the provided document and policies. Avoid generic advice.\n"
            "For each gap, provide 2-3 concrete steps that can be implemented.\n\n"
            "JSON Schema: {\n"
            "  \"regulation\": {\"name\": \"string\", \"jurisdiction\": \"string|null\", \"type\": \"string\"},\n"
            "  \"overall\": {\"status\": \"compliant|partially_compliant|non_compliant\", \"score\": 0, \"summary\": \"string\"},\n"
            "  \"sections\": [{\n"
            "    \"name\": \"string\", \"status\": \"compliant|partially_compliant|non_compliant\", \"score\": 0,\n"
            "    \"gaps\": [{\n"
            "      \"gap_id\": \"string\", \"description\": \"string\", \"risk_level\": \"high|medium|low\",\n"
            "      \"evidence\": \"string|null\", \"recommendations\": [\"string\"]\n"
            "    }]\n"
            "  }],\n"
            "  \"top_recommendations\": [\"string\"],\n"
            "  \"detected_framework\": \"string\",\n"
            "  \"assumptions\": [\"string\"]\n"
            "}\n"
            "Return only JSON."
        )

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            raw = (response.text or "").strip()
            try:
                parsed = json.loads(raw)
            except Exception:
                # Minimal fallback if model doesn't return JSON
                parsed = {
                    "regulation": {"name": "unknown", "jurisdiction": None, "type": regulation_analysis.get("regulation_type", "general")},
                    "overall": {"status": "partially_compliant", "score": 60, "summary": raw[:300]},
                    "sections": [],
                    "top_recommendations": [],
                    "detected_framework": "unknown",
                    "assumptions": []
                }

            # Normalize to API shape expected by frontend/backend
            overall_status = parsed.get("overall", {}).get("status", "partially_compliant")
            compliance_score = parsed.get("overall", {}).get("score", 60)
            gaps = []
            for s in parsed.get("sections", []):
                for i, g in enumerate(s.get("gaps", []), 1):
                    gaps.append({
                        "gap_id": g.get("gap_id") or f"{s.get('name','SEC')}-{i}",
                        "requirement": s.get("name", "Unknown"),
                        "current_state": "unknown",
                        "gap_description": g.get("description", ""),
                        "impact_level": g.get("risk_level", "medium"),
                        "remediation_effort": "medium",
                        "recommended_actions": g.get("recommendations", []),
                    })

            recommendations = parsed.get("top_recommendations", [])
            if not recommendations:
                # Build recommendations from gaps if top_recommendations missing
                rec_set = []
                for g in gaps:
                    for r in g.get("recommended_actions", []) or []:
                        if r and r not in rec_set:
                            rec_set.append(r)
                recommendations = rec_set
            
            # If still no recommendations, provide some based on the regulation type
            if not recommendations:
                if "gdpr" in hint_type.lower():
                    recommendations = [
                        "Implement data subject rights management system",
                        "Conduct Data Protection Impact Assessments (DPIAs)",
                        "Establish data breach notification procedures",
                        "Review and update privacy notices",
                        "Implement data minimization practices"
                    ]
                elif "hipaa" in hint_type.lower():
                    recommendations = [
                        "Implement PHI access controls and audit logs",
                        "Conduct risk assessments for all PHI systems",
                        "Establish Business Associate Agreements (BAAs)",
                        "Implement workforce training on PHI handling",
                        "Develop incident response procedures"
                    ]
                else:
                    recommendations = [
                        "Conduct comprehensive compliance review",
                        "Develop detailed action plan with timelines",
                        "Assign compliance responsibilities to team members",
                        "Implement regular monitoring and reporting",
                        "Establish training programs for staff"
                    ]

            return {
                "overall_status": overall_status,
                "compliance_score": compliance_score,
                "gaps": gaps,
                "recommendations": recommendations,
                "detailed_analysis": parsed,
            }
        except Exception as e:
            logger.error(f"Error in check_compliance: {str(e)}")
            # Provide fallback recommendations based on regulation type
            fallback_recs = []
            if "gdpr" in hint_type.lower():
                fallback_recs = [
                    "Implement data subject rights management system",
                    "Conduct Data Protection Impact Assessments (DPIAs)",
                    "Establish data breach notification procedures"
                ]
            elif "hipaa" in hint_type.lower():
                fallback_recs = [
                    "Implement PHI access controls and audit logs",
                    "Conduct risk assessments for all PHI systems",
                    "Establish Business Associate Agreements (BAAs)"
                ]
            else:
                fallback_recs = [
                    "Conduct comprehensive compliance review",
                    "Develop detailed action plan with timelines",
                    "Assign compliance responsibilities to team members"
                ]
            
            return {
                "overall_status": "partially_compliant",
                "compliance_score": 60,
                "gaps": [],
                "recommendations": fallback_recs,
                "detailed_analysis": {"error": str(e)},
            }