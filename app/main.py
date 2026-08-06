from fastapi import FastAPI
import os
import platform

app = FastAPI(
    title="Automated Software Release Management System",
    description="Sample Microservice for DevOps CI/CD Pipeline Demo",
    version="1.0.0"
)

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
