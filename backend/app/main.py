import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="HCP Log Interaction CRM API",
        version="1.0.0",
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.api import api_router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application

app = get_application()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up HCP Log Interaction Backend...")

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}
