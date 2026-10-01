
from pydantic import BaseModel, Field

from src.config import WEIGHTS


class ParsedResume(BaseModel):
    file_name: str
    file_hash: str = ""            
    text: str = ""                 
    links: list[str] = []          
    name: str | None = None
    email: str | None = None
    github_username: str | None = None
    sections: dict[str, str] = {}  
    parse_error: str | None = None 

class EligibilityResult(BaseModel):
    candidate: str
    eligible: bool
    rejection_reasons: list[str] = []
    matched_skills: list[str] = []
    evidence: list[str] = []  


class ScoreBreakdown(BaseModel):
    ai_project_depth: int = Field(0, ge=0, le=WEIGHTS["ai_project_depth"])
    python_backend: int = Field(0, ge=0, le=WEIGHTS["python_backend"])
    cloud_fullstack: int = Field(0, ge=0, le=WEIGHTS["cloud_fullstack"])
    github: int = Field(0, ge=0, le=WEIGHTS["github"])
    engineering_depth: int = Field(0, ge=0, le=WEIGHTS["engineering_depth"])

    def total(self) -> int:
        return sum(self.model_dump().values())    


class GitHubResult(BaseModel):
    status: str = "no_profile"     
    summary: str = ""
    activity_score: int = Field(0, ge=0, le=5)
    repo_score: int = Field(0, ge=0, le=5)
    error: str | None = None   

class CandidateResult(BaseModel):
    rank: int | None = None        
    candidate_name: str
    file_name: str
    email: str | None = None
    github_url: str | None = None
    eligible: bool
    total_score: int | None = None
    score_breakdown: ScoreBreakdown | None = None
    matched_skills: list[str] = []
    rejection_reasons: list[str] = []
    project_summary: str = ""
    github_summary: str = ""
    github_status: str = ""
    llm_status: str = ""
    strengths: list[str] = []
    concerns: list[str] = []
    evidence: dict[str, list[str]] = {}  

class ScoringResult(BaseModel):
    breakdown: ScoreBreakdown
    total_score: int
    evidence: dict[str, list[str]] = {}
    strengths: list[str] = []
    concerns: list[str] = []
    project_summary: str = ""


class ProjectJudgement(BaseModel):
    ai_depth_score: int = Field(ge=0, le=40)
    is_thin_wrapper: bool
    reason: str
    evidence_quote: str