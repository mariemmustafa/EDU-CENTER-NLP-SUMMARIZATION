
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.dependencies import initialize_dependencies
from app.presentation.routes import router as summarize_router
from app.presentation.health import router as health_router
from app.utils.exceptions import SummarizationError
from app.utils.logger import get_logger, set_request_id

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NLP service")
    try:
        await initialize_dependencies()
        logger.info("NLP service ready")
    except Exception as e:
        logger.error(f"Failed to initialize dependencies: {e}", exc_info=True)
        raise
    yield
    logger.info("NLP service shutting down")


app = FastAPI(
    title="NLP Summarization Service",
    version="2.0.0",
    description="Production-ready PDF summarization microservice",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware: inject request_id into every request's logging context
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # Use X-Request-ID header if provided, otherwise generate one
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    set_request_id(request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(SummarizationError)
async def summarization_error_handler(_request: Request, exc: SummarizationError):
    logger.error(f"Summarization error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(Exception)
async def generic_error_handler(_request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(summarize_router)


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
