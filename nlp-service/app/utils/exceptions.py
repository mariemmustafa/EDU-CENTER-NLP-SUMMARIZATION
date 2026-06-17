class SummarizationError(Exception):
    """Base exception for all service errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ProviderError(SummarizationError):
    """AI provider failed to produce a summary."""

    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"Provider '{provider}' error: {message}",
            status_code=502,
        )
        self.provider = provider


class ValidationError(SummarizationError):
    """Generic input validation failure."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)


class InvalidFileError(ValidationError):
    """Uploaded file is not a valid PDF."""

    def __init__(self, reason: str):
        super().__init__(message=f"Invalid PDF file: {reason}")


class FileTooLargeError(ValidationError):
    """Uploaded file exceeds the size limit."""

    def __init__(self, size_mb: float, max_mb: int):
        super().__init__(
            message=f"File size ({size_mb:.1f} MB) exceeds limit ({max_mb} MB)"
        )


class PageRangeError(ValidationError):
    """Requested page range is out of bounds."""

    def __init__(self, message: str):
        super().__init__(message=f"Invalid page range: {message}")


class ExtractionError(SummarizationError):
    """Failed to extract text from document."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Text extraction failed: {reason}",
            status_code=422,
        )


class EmptyTextError(ValidationError):
    """PDF contains no extractable text."""

    def __init__(self):
        super().__init__(
            message="PDF contains no extractable text (possibly scanned/image-only)"
        )


class TextTooLongError(SummarizationError):
    """Extracted text exceeds processing limit."""

    def __init__(self, length: int, max_length: int):
        super().__init__(
            message=f"Text length ({length}) exceeds maximum ({max_length})",
            status_code=413,
        )
