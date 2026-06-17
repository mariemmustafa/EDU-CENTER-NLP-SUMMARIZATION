from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Provider ---
    summarization_provider: str = "huggingface"
    fallback_provider: str = ""  # e.g. "huggingface" when primary is "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    huggingface_model: str = "Falconsai/text_summarization"
    multilingual_huggingface_model: str = "malmarjeh/t5-arabic-text-summarization"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # --- Limits ---
    max_file_size_mb: int = 20
    max_input_length: int = 50000

    # --- Chunking ---
    chunk_max_tokens: int = 500
    chunk_overlap: int = 20

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
