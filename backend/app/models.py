"""
ElasticSeer Data Models

Pydantic v2 models for core data structures used throughout the ElasticSeer platform.
All models include validation rules per design specifications.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Enums
# ============================================================================

class Severity(str, Enum):
    """Incident severity levels"""
    SEV_1 = "Sev-1"
    SEV_2 = "Sev-2"
    SEV_3 = "Sev-3"


class IncidentStatus(str, Enum):
    """Incident lifecycle status"""
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    INITIALIZING = "INITIALIZING"
    RESEARCHING = "RESEARCHING"
    CORRELATING = "CORRELATING"
    DIAGNOSING = "DIAGNOSING"
    REMEDIATING = "REMEDIATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentType(str, Enum):
    """Agent types in the multi-agent system"""
    RESEARCHER = "RESEARCHER"
    CORRELATOR = "CORRELATOR"
    DIAGNOSER = "DIAGNOSER"
    REMEDIATOR = "REMEDIATOR"


class EvidenceType(str, Enum):
    """Types of evidence for diagnosis"""
    CODE_DIFF = "CODE_DIFF"
    LOG_ENTRY = "LOG_ENTRY"
    METRIC_SPIKE = "METRIC_SPIKE"
    PAST_INCIDENT = "PAST_INCIDENT"


class ReferenceType(str, Enum):
    """Types of grounding references"""
    PAST_FIX = "PAST_FIX"
    DOCUMENTATION = "DOCUMENTATION"
    BEST_PRACTICE = "BEST_PRACTICE"


# ============================================================================
# Core Data Models
# ============================================================================

class MetricDataPoint(BaseModel):
    """
    Represents a single metric observation from the monitoring system.
    
    Validation:
    - timestamp must be within last 30 days
    - value must be non-negative for latency/throughput metrics
    """
    timestamp: datetime = Field(..., description="When the metric was observed")
    metric_name: str = Field(..., description="Name of the metric (e.g., p99_latency, error_rate)")
    value: float = Field(..., description="Metric value")
    service: str = Field(..., description="Service name")
    environment: str = Field(..., description="Environment (prod, staging, dev)")
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional metadata tags")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Timestamp must be within last 30 days"""
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        if v < thirty_days_ago:
            raise ValueError(f"Timestamp must be within last 30 days, got {v}")
        if v > now:
            raise ValueError(f"Timestamp cannot be in the future, got {v}")
        return v
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: float, info) -> float:
        """Value must be non-negative for latency/throughput metrics"""
        # Get metric_name from the validation context if available
        if hasattr(info, 'data') and 'metric_name' in info.data:
            metric_name = info.data['metric_name']
            if metric_name in ['p99_latency', 'p95_latency', 'throughput', 'request_count']:
                if v < 0:
                    raise ValueError(f"{metric_name} must be non-negative, got {v}")
        return v


class Baseline(BaseModel):
    """
    Statistical baseline for anomaly detection using 7-day rolling window.
    
    Validation:
    - mean, stddev, threshold must be non-negative
    - threshold = mean + 3 * stddev
    """
    mean: float = Field(..., description="Mean value over baseline window", ge=0)
    stddev: float = Field(..., description="Standard deviation", ge=0)
    threshold: float = Field(..., description="Anomaly threshold (mean + 3*stddev)", ge=0)
    calculated_at: datetime = Field(..., description="When baseline was calculated")
    
    @model_validator(mode='after')
    def validate_threshold(self) -> 'Baseline':
        """
        Threshold must equal mean + 3 * stddev, except when stddev is 0.
        When stddev is 0, threshold should be mean * 1.1 (Requirement 1.8)
        """
        if self.stddev == 0:
            # Special case: when stddev is 0, threshold = mean * 1.1
            expected_threshold = self.mean * 1.1
        else:
            # Normal case: threshold = mean + 3 * stddev
            expected_threshold = self.mean + (3 * self.stddev)
        
        if abs(self.threshold - expected_threshold) > 0.01:  # Allow small floating point errors
            raise ValueError(
                f"Threshold validation failed. "
                f"Expected {expected_threshold}, got {self.threshold}"
            )
        return self


class AnomalyResult(BaseModel):
    """
    Detected anomaly with severity classification.
    
    Validation:
    - severity must be Sev-1, Sev-2, or Sev-3
    - deviation_sigma >= 3.0 for valid anomalies
    """
    metric: str = Field(..., description="Metric name that triggered anomaly")
    current_value: float = Field(..., description="Current observed value")
    expected_value: float = Field(..., description="Expected value (baseline mean)")
    deviation_sigma: float = Field(..., description="Number of standard deviations from mean", ge=3.0)
    severity: Severity = Field(..., description="Severity classification")
    detected_at: datetime = Field(..., description="When anomaly was detected")
    service: Optional[str] = Field(None, description="Affected service")
    environment: Optional[str] = Field(None, description="Environment")
    
    @model_validator(mode='after')
    def validate_severity_matches_deviation(self) -> 'AnomalyResult':
        """Severity must match deviation: >=5σ → Sev-1, 3-5σ → Sev-2"""
        if self.deviation_sigma >= 5.0 and self.severity != Severity.SEV_1:
            raise ValueError(f"Deviation {self.deviation_sigma}σ should be Sev-1")
        elif 3.0 <= self.deviation_sigma < 5.0 and self.severity != Severity.SEV_2:
            raise ValueError(f"Deviation {self.deviation_sigma}σ should be Sev-2")
        return self


class TimeRange(BaseModel):
    """Time window for queries and analysis"""
    start: datetime = Field(..., description="Start time")
    end: datetime = Field(..., description="End time")
    
    @model_validator(mode='after')
    def validate_time_range(self) -> 'TimeRange':
        """Start must be before end"""
        if self.start >= self.end:
            raise ValueError(f"Start time {self.start} must be before end time {self.end}")
        return self


# ============================================================================
# Evidence and Reasoning Models
# ============================================================================

class Evidence(BaseModel):
    """
    Evidence supporting diagnosis with grounding guarantee.
    
    Validation:
    - relevance must be between 0.0 and 1.0
    """
    type: EvidenceType = Field(..., description="Type of evidence")
    content: str = Field(..., description="Evidence content")
    source: str = Field(..., description="Source reference")
    relevance: float = Field(..., description="Relevance score", ge=0.0, le=1.0)


class ReasoningStep(BaseModel):
    """Single step in reasoning trace"""
    step: int = Field(..., description="Step number", ge=1)
    description: str = Field(..., description="Step description")
    conclusion: str = Field(..., description="Conclusion from this step")
    supporting_evidence: List[Evidence] = Field(..., description="Evidence supporting this step")
    
    @field_validator('supporting_evidence')
    @classmethod
    def validate_evidence_exists(cls, v: List[Evidence]) -> List[Evidence]:
        """Each reasoning step must have at least one piece of evidence"""
        if len(v) == 0:
            raise ValueError("Reasoning step must have at least one piece of supporting evidence")
        return v


class Diagnosis(BaseModel):
    """
    Root cause diagnosis with evidence grounding.
    
    Validation:
    - confidence must be between 0.0 and 1.0
    - must have at least 3 reasoning steps
    """
    root_cause: str = Field(..., description="Root cause explanation")
    affected_component: str = Field(..., description="Component affected by the issue")
    impact_explanation: str = Field(..., description="How the issue impacts the system")
    evidence: List[Evidence] = Field(..., description="Supporting evidence")
    confidence: float = Field(..., description="Confidence score", ge=0.0, le=1.0)
    reasoning: List[ReasoningStep] = Field(..., description="Step-by-step reasoning trace")
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning_steps(cls, v: List[ReasoningStep]) -> List[ReasoningStep]:
        """Must have at least 3 reasoning steps"""
        if len(v) < 3:
            raise ValueError(f"Diagnosis must have at least 3 reasoning steps, got {len(v)}")
        return v


class Reference(BaseModel):
    """Grounding reference for code fixes"""
    type: ReferenceType = Field(..., description="Type of reference")
    source: str = Field(..., description="Source identifier")
    excerpt: str = Field(..., description="Relevant excerpt")


# ============================================================================
# Code and Commit Models
# ============================================================================

class Commit(BaseModel):
    """
    Git commit with suspicion scoring.
    
    Validation:
    - suspicion_score must be between 0.0 and 1.0
    """
    sha: str = Field(..., description="Commit SHA")
    author: str = Field(..., description="Commit author")
    message: str = Field(..., description="Commit message")
    timestamp: datetime = Field(..., description="Commit timestamp")
    files_changed: List[str] = Field(..., description="List of changed file paths")
    diff_summary: str = Field(..., description="Summary of changes")
    suspicion_score: float = Field(..., description="Suspicion score", ge=0.0, le=1.0)


class CodeFix(BaseModel):
    """
    Generated code fix with grounding references.
    
    Validation:
    - must have at least one grounding reference
    """
    file_path: str = Field(..., description="Path to file being fixed")
    original_code: str = Field(..., description="Original code")
    fixed_code: str = Field(..., description="Fixed code")
    explanation: str = Field(..., description="Explanation of the fix")
    diff_preview: str = Field(..., description="Diff preview")
    grounding_references: List[Reference] = Field(..., description="Grounding references")
    
    @field_validator('grounding_references')
    @classmethod
    def validate_grounding(cls, v: List[Reference]) -> List[Reference]:
        """Must have at least one grounding reference"""
        if len(v) == 0:
            raise ValueError("Code fix must have at least one grounding reference")
        return v


# ============================================================================
# Search and Retrieval Models
# ============================================================================

class SearchResult(BaseModel):
    """
    Hybrid search result with BM25 and vector scores.
    
    Validation:
    - all scores must be between 0.0 and 1.0
    - combined_score = 0.5 * bm25_score + 0.5 * vector_score
    """
    document: Dict[str, Any] = Field(..., description="Retrieved document")
    bm25_score: float = Field(..., description="BM25 keyword score", ge=0.0, le=1.0)
    vector_score: float = Field(..., description="Vector similarity score", ge=0.0, le=1.0)
    combined_score: float = Field(..., description="Combined score", ge=0.0, le=1.0)
    highlights: List[str] = Field(default_factory=list, description="Highlighted excerpts")
    
    @model_validator(mode='after')
    def validate_combined_score(self) -> 'SearchResult':
        """Combined score must equal 0.5 * bm25 + 0.5 * vector"""
        expected = 0.5 * self.bm25_score + 0.5 * self.vector_score
        if abs(self.combined_score - expected) > 0.01:
            raise ValueError(
                f"Combined score must equal 0.5*bm25 + 0.5*vector. "
                f"Expected {expected}, got {self.combined_score}"
            )
        return self


# ============================================================================
# Workflow and Agent Models
# ============================================================================

class Context(BaseModel):
    """Workflow context shared between agents"""
    incident_id: str = Field(..., description="Unique incident identifier")
    anomaly: AnomalyResult = Field(..., description="Detected anomaly")
    time_window: TimeRange = Field(..., description="Time window for analysis")
    affected_services: List[str] = Field(..., description="List of affected services")
    shared_state: Dict[str, Any] = Field(default_factory=dict, description="Shared state between agents")


class AgentResult(BaseModel):
    """
    Result from agent execution.
    
    Validation:
    - confidence must be between 0.0 and 1.0
    """
    agent_type: AgentType = Field(..., description="Type of agent")
    status: str = Field(..., description="Execution status (SUCCESS, FAILED)")
    findings: List[Dict[str, Any]] = Field(..., description="Agent findings")
    confidence: float = Field(..., description="Confidence in results", ge=0.0, le=1.0)
    execution_time: float = Field(..., description="Execution time in seconds", ge=0.0)


class AgentState(BaseModel):
    """
    Workflow state tracking agent execution.
    
    Validation:
    - status transitions must follow valid state machine
    """
    workflow_id: str = Field(..., description="Workflow identifier")
    current_agent: Optional[AgentType] = Field(None, description="Currently executing agent")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    context: Context = Field(..., description="Workflow context")
    results: Dict[str, AgentResult] = Field(default_factory=dict, description="Agent results by type")
    started_at: datetime = Field(..., description="Workflow start time")
    last_updated_at: datetime = Field(..., description="Last update time")
    
    @model_validator(mode='after')
    def validate_state_consistency(self) -> 'AgentState':
        """Validate workflow state consistency"""
        # When status is RESEARCHING, current_agent must be RESEARCHER
        if self.status == WorkflowStatus.RESEARCHING and self.current_agent != AgentType.RESEARCHER:
            raise ValueError("Status RESEARCHING requires current_agent=RESEARCHER")
        
        # When status is CORRELATING, current_agent must be CORRELATOR
        if self.status == WorkflowStatus.CORRELATING and self.current_agent != AgentType.CORRELATOR:
            raise ValueError("Status CORRELATING requires current_agent=CORRELATOR")
        
        # When status is DIAGNOSING, current_agent must be DIAGNOSER
        if self.status == WorkflowStatus.DIAGNOSING and self.current_agent != AgentType.DIAGNOSER:
            raise ValueError("Status DIAGNOSING requires current_agent=DIAGNOSER")
        
        # When status is REMEDIATING, current_agent must be REMEDIATOR
        if self.status == WorkflowStatus.REMEDIATING and self.current_agent != AgentType.REMEDIATOR:
            raise ValueError("Status REMEDIATING requires current_agent=REMEDIATOR")
        
        return self


class DiagnosisReport(BaseModel):
    """
    Complete diagnosis report for human approval.
    
    Validation:
    - confidence must be between 0.0 and 1.0
    """
    root_cause: str = Field(..., description="Root cause")
    evidence: List[Evidence] = Field(..., description="Supporting evidence")
    proposed_fix: CodeFix = Field(..., description="Proposed code fix")
    confidence: float = Field(..., description="Confidence score", ge=0.0, le=1.0)
    reasoning_trace: List[ReasoningStep] = Field(..., description="Full reasoning trace")


# ============================================================================
# Incident Management Models
# ============================================================================

class IncidentRecord(BaseModel):
    """
    Complete incident record for audit and learning.
    
    Validation:
    - severity must be Sev-1, Sev-2, or Sev-3
    - status transitions must follow valid state machine
    - mttr must be non-negative if resolved
    """
    id: str = Field(..., description="Incident identifier")
    severity: Severity = Field(..., description="Incident severity")
    status: IncidentStatus = Field(..., description="Current status")
    anomaly: AnomalyResult = Field(..., description="Detected anomaly")
    diagnosis: Optional[Diagnosis] = Field(None, description="Root cause diagnosis")
    remediation: Optional[CodeFix] = Field(None, description="Applied fix")
    timeline: List[Dict[str, Any]] = Field(default_factory=list, description="Event timeline")
    created_at: datetime = Field(..., description="Incident creation time")
    resolved_at: Optional[datetime] = Field(None, description="Resolution time")
    mttr: Optional[float] = Field(None, description="Mean Time To Remediation in seconds", ge=0.0)
    
    @model_validator(mode='after')
    def validate_incident_consistency(self) -> 'IncidentRecord':
        """Validate incident record consistency"""
        # If status is RESOLVED, must have resolved_at and mttr
        if self.status == IncidentStatus.RESOLVED:
            if self.resolved_at is None:
                raise ValueError("RESOLVED status requires resolved_at timestamp")
            if self.mttr is None:
                raise ValueError("RESOLVED status requires mttr value")
            
            # MTTR should match time difference
            expected_mttr = (self.resolved_at - self.created_at).total_seconds()
            if abs(self.mttr - expected_mttr) > 1.0:  # Allow 1 second tolerance
                raise ValueError(
                    f"MTTR {self.mttr}s doesn't match time difference {expected_mttr}s"
                )
        
        # If status is RESOLVED, should have diagnosis and remediation
        if self.status == IncidentStatus.RESOLVED:
            if self.diagnosis is None:
                raise ValueError("RESOLVED incidents should have diagnosis")
            if self.remediation is None:
                raise ValueError("RESOLVED incidents should have remediation")
        
        return self


# ============================================================================
# Configuration Models
# ============================================================================

class EmbeddingConfig(BaseModel):
    """
    Configuration for embeddings.
    
    Validation:
    - dimensions must be 768 for Elastic Inference API
    """
    dimensions: int = Field(768, description="Embedding dimensions")
    model: str = Field("elastic-inference", description="Embedding model")
    
    @field_validator('dimensions')
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        """Embedding must be 768-dimensional"""
        if v != 768:
            raise ValueError(f"Embedding dimensions must be 768, got {v}")
        return v
