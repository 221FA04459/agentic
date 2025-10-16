"""
Pydantic models for Compliance API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RegulationDocument(BaseModel):
    id: str
    filename: str
    file_path: str
    regulation_type: str
    jurisdiction: str
    effective_date: Optional[str]
    extracted_text: str
    analysis_result: Dict[str, Any]
    upload_date: str
    status: str


class ComplianceCheck(BaseModel):
    regulation_id: str
    company_policies: List[str] = Field(default_factory=list)
    specific_requirements: Optional[List[str]] = None


class ComplianceReport(BaseModel):
    regulation_id: str
    include_recommendations: bool = True
    include_gap_analysis: bool = True
    include_policy_mapping: bool = True

"""
Pydantic models for the Compliance Officer API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class RegulationType(str, Enum):
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    CCPA = "ccpa"
    GENERAL = "general"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    PENDING = "pending"
    ERROR = "error"

class RegulationUpload(BaseModel):
    filename: str
    regulation_type: RegulationType = RegulationType.GENERAL
    jurisdiction: str = "global"
    effective_date: Optional[str] = None

class RegulationDocument(BaseModel):
    id: str
    filename: str
    file_path: str
    regulation_type: str
    jurisdiction: str
    effective_date: Optional[str]
    extracted_text: str
    analysis_result: Dict[str, Any]
    upload_date: str
    status: str

class ComplianceCheck(BaseModel):
    regulation_id: str
    company_policies: List[str] = Field(
        default_factory=list,
        description="List of company policy documents or descriptions"
    )
    specific_requirements: Optional[List[str]] = Field(
        default=None,
        description="Specific compliance requirements to check"
    )

class ComplianceResult(BaseModel):
    overall_status: ComplianceStatus
    compliance_score: float = Field(ge=0, le=100)
    gaps: List[Dict[str, Any]]
    recommendations: List[str]
    detailed_analysis: Dict[str, Any]

class ComplianceReport(BaseModel):
    regulation_id: str
    include_recommendations: bool = True
    include_gap_analysis: bool = True
    include_policy_mapping: bool = True

class PolicyRequirement(BaseModel):
    requirement_id: str
    description: str
    category: str
    priority: str  # high, medium, low
    applicable_sections: List[str]

class ComplianceGap(BaseModel):
    gap_id: str
    requirement: str
    current_state: str
    gap_description: str
    impact_level: str  # high, medium, low
    remediation_effort: str  # high, medium, low
    recommended_actions: List[str]

class AIAnalysisResult(BaseModel):
    regulation_summary: str
    key_requirements: List[PolicyRequirement]
    compliance_obligations: List[str]
    risk_assessment: Dict[str, Any]
    implementation_timeline: Optional[str] = None
    affected_departments: List[str] = []

class ReportMetadata(BaseModel):
    report_id: str
    regulation_id: str
    generated_date: str
    format: str
    file_path: str
    file_size: Optional[int] = None

class APIError(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
