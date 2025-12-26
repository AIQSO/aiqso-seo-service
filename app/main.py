from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.routers import audits, billing, clients, health, keywords, odoo, portal, reports, websites, worklog
from app.security import require_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    settings.validate_runtime()
    init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AIQSO SEO Service API

    Enterprise SEO auditing, rank tracking, and optimization platform.

    ## Features

    - **Technical SEO Audits**: 24+ checks for meta tags, content, performance
    - **Rank Tracking**: Daily keyword position monitoring
    - **Performance Audits**: Google Lighthouse integration
    - **AI-Powered Insights**: Content analysis using Claude
    - **White-Label Reports**: PDF exports with custom branding

    ## Authentication

    Use Bearer token authentication with your API key:
    ```
    Authorization: Bearer your_api_key_here
    ```
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
auth_dependencies = [Depends(require_client)]

app.include_router(
    clients.router,
    prefix=f"{settings.api_prefix}/clients",
    tags=["Clients"],
    dependencies=auth_dependencies,
)
app.include_router(
    websites.router,
    prefix=f"{settings.api_prefix}/websites",
    tags=["Websites"],
    dependencies=auth_dependencies,
)
app.include_router(
    audits.router,
    prefix=f"{settings.api_prefix}/audits",
    tags=["Audits"],
    dependencies=auth_dependencies,
)
app.include_router(
    keywords.router,
    prefix=f"{settings.api_prefix}/keywords",
    tags=["Keywords"],
    dependencies=auth_dependencies,
)
app.include_router(
    reports.router,
    prefix=f"{settings.api_prefix}/reports",
    tags=["Reports"],
    dependencies=auth_dependencies,
)

# New routers for customer platform
app.include_router(billing.router, prefix=f"{settings.api_prefix}", tags=["Billing"])
app.include_router(
    worklog.router,
    prefix=f"{settings.api_prefix}",
    tags=["Work Log"],
    dependencies=auth_dependencies,
)
app.include_router(
    portal.router,
    prefix=f"{settings.api_prefix}",
    tags=["Customer Portal"],
    dependencies=auth_dependencies,
)
app.include_router(
    odoo.router,
    prefix=f"{settings.api_prefix}",
    tags=["Odoo Integration"],
    dependencies=auth_dependencies,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
