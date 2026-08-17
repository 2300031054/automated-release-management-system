from pydantic import BaseModel


class ReleaseIndicators(BaseModel):
    build_passed: bool
    test_pass_rate: float
    code_quality_score: float
    critical_vulns: int = 0
    high_vulns: int = 0
    previous_release_success_rate: float
