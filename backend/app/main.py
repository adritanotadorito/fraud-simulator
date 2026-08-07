from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database import connect_to_mongo, close_mongo_connection, get_database, count_documents
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Fraud Shield AI...")
    await connect_to_mongo()
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
    except Exception as e:
        logger.warning(f"Startup check skipped: {e}")
    yield
    logger.info("Shutting down Fraud Shield AI...")
    await close_mongo_connection()


app = FastAPI(
    title="Fraud Shield AI",
    description="Real-Time Adversarial Fraud Detection & Prevention Platform — FraudGPT vs ShieldGPT",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Fraud Shield AI API", "version": "1.0.0", "status": "active"}


@app.get("/health", tags=["Health"])
async def health_check():
    try:
        db = get_database()
        return {"status": "healthy", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "disconnected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
