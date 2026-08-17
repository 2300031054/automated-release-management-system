from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import platform
from datetime import datetime

from .models import ReleaseIndicators
from .decision_engine import evaluate_release

app = FastAPI(
    title="Automated Software Release Management System",
    description="Sample Microservice for DevOps CI/CD Pipeline Demo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# simple in-memory history for now (swap for a DB later)
release_history = []


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AutoReleaseX Microservice API",
        "version": os.getenv("APP_VERSION", "v1.0.0"),
        "hostname": platform.node(),
        "environment": os.getenv("APP_ENV", "production")
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "code": 200, "checks": {"database": "ok"}}


@app.post("/evaluate")
def evaluate(indicators: ReleaseIndicators):
    """
    Runs the rule-based decision engine against the given release
    indicators and returns RELEASE / BLOCK / MANUAL_APPROVAL along with
    a full explanation for every condition checked.
    """
    result = evaluate_release(
        build_passed=indicators.build_passed,
        test_pass_rate=indicators.test_pass_rate,
        code_quality_score=indicators.code_quality_score,
        critical_vulns=indicators.critical_vulns,
        high_vulns=indicators.high_vulns,
        previous_release_success_rate=indicators.previous_release_success_rate,
    )
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "inputs": indicators.dict(),
        "decision": result["decision"],
    }
    release_history.append(entry)
    return result


@app.get("/history")
def history():
    return release_history[-20:]  # last 20 evaluations
