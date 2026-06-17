from pydantic import BaseModel, field_validator


class SummarizeRequest(BaseModel):
    """Validated request parameters for summarization."""
    start_page: int | None = None
    end_page: int | None = None
    request_id: str | None = None

    @field_validator("start_page", "end_page", mode="before")
    @classmethod
    def coerce_empty_to_none(cls, v):
        if v is None or v == "":
            return None
        return int(v)

    @field_validator("start_page", "end_page")
    @classmethod
    def page_must_be_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError("Page numbers must be >= 1")
        return v


class SummarizationResponse(BaseModel):
    status: str = "success"
    original_length: int
    summary_length: int
    compression_ratio: float
    summary_text: str
