from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base
from app.api import auth, users, analytics, views, documents, processing, reviews, reports, schedules


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and storage directories exist
    Base.metadata.create_all(bind=engine)
    settings.uploads_path
    settings.reports_path
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.APP_NAME,
    description="Intelligent Document Processing & Workflow Automation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response

# Mount static assets
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include API and View routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(processing.router)
app.include_router(reviews.router)
app.include_router(reports.router)
app.include_router(schedules.router)
app.include_router(analytics.router)
app.include_router(views.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": "connected"
    }


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "API endpoint not found."})
    return JSONResponse(status_code=404, content={"detail": "Page not found."})
