import uuid

from fastapi import APIRouter, File, UploadFile, Form

from app.domain.entities import SummarizationResponse
from app.dependencies import get_use_case

router = APIRouter(prefix="/api/v1", tags=["summarization"])


@router.post("/summarize", response_model=SummarizationResponse)
async def summarize(
    file: UploadFile = File(..., description="PDF file to summarize"),
    start_page: int | None = Form(None, description="Start page (1-based, inclusive)"),
    end_page: int | None = Form(None, description="End page (1-based, inclusive)"),
    request_id: str | None = Form(None, description="Request tracing ID"),
):
    """
    Upload a PDF and receive a structured summary.

    All validation (file type, size, page range) is handled by the use case.
    Errors are returned as structured JSON via exception handlers.
    """
    # Auto-generate request_id if not provided
    rid = request_id or uuid.uuid4().hex[:12]

    content = await file.read()

    use_case = get_use_case()
    return await use_case.execute(
        content=content,
        filename=file.filename or "unknown.pdf",
        start_page=start_page,
        end_page=end_page,
        request_id=rid,
    )
