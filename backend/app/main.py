"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, dev, employees, notifications, payroll, rules, shifts

settings = get_settings()

app = FastAPI(
    title="AI-Shifts-Management API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health Check"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


app.include_router(auth.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(shifts.router, prefix="/api")
app.include_router(payroll.router, prefix="/api")
app.include_router(dev.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
