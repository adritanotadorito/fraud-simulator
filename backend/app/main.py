from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.database import connect_to_mongo, close_mongo_connection, get_database, count_documents, is_connected
from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from app.routers.transactions import router as transactions_router
from app.routers.fraud import router as fraud_router
from app.routers.shield import router as shield_router
from app.routers.biometrics import router as biometrics_router
from app.routers.device import router as device_router
from app.routers.geo import router as geo_router
from app.routers.graph import router as graph_router
from app.routers.threat_intel import router as threat_intel_router
from app.routers.metrics import router as metrics_router
from app.routers.reports import router as reports_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Starting Fraud Shield AI v1.0.0")
    logger.info("=" * 60)
    await connect_to_mongo()

    if is_connected():
        try:
            users_count = await count_documents("users", {})
            if users_count == 0:
                logger.info("Database empty — seeding with digital twin data...")
                try:
                    from data.digital_twin import DigitalTwinGenerator
                    db = get_database()
                    generator = DigitalTwinGenerator()
                    await generator.seed_database(db)
                    logger.info("Database seeded successfully.")
                except Exception as e:
                    logger.warning(f"Could not seed database: {e}")
            else:
                logger.info(f"Database has {users_count} users. Skipping seed.")

            # Log collection counts
            for coll in ["users", "accounts", "devices", "sessions", "transactions"]:
                count = await count_documents(coll, {})
                logger.info(f"  {coll}: {count} documents")
        except Exception as e:
            logger.warning(f"Startup check skipped: {e}")
    else:
        logger.warning("MongoDB not available. Running in degraded mode (API endpoints that need DB will fail).")

    logger.info("Fraud Shield AI is ready!")
    yield
    logger.info("Shutting down Fraud Shield AI...")
    await close_mongo_connection()


app = FastAPI(
    title="Fraud Shield AI",
    description="Real-Time Adversarial Fraud Detection & Prevention Platform — FraudGPT vs ShieldGPT",
    version="1.0.0",
    lifespan=lifespan
)


# ---- Middleware ----

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with latency tracking."""
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        latency = (time.time() - start) * 1000
        logger.error(f"{request.method} {request.url.path} → 500 ({latency:.0f}ms) ERROR: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)}
        )
    latency = (time.time() - start) * 1000
    log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
    # Skip noisy health check logs
    if request.url.path not in ["/", "/health"]:
        logger.log(log_level, f"{request.method} {request.url.path} → {response.status_code} ({latency:.0f}ms)")
    return response


# ---- Routers ----

app.include_router(transactions_router)
app.include_router(fraud_router)
app.include_router(shield_router)
app.include_router(biometrics_router)
app.include_router(device_router)
app.include_router(geo_router)
app.include_router(graph_router)
app.include_router(threat_intel_router)
app.include_router(metrics_router)
app.include_router(reports_router)
app.include_router(auth_router)
app.include_router(admin_router)


# ---- Health Endpoints ----

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Fraud Shield AI API", "version": "1.0.0", "status": "active"}


@app.get("/health", tags=["Health"])
async def health_check():
    db_status = "connected" if is_connected() else "disconnected"
    return {
        "status": "healthy" if is_connected() else "degraded",
        "db": db_status,
        "version": "1.0.0"
    }


# ---- Global Error Handlers ----

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.error(f"RuntimeError on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Service unavailable", "error": str(exc)}
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
