import asyncio

from openai import AsyncOpenAI

from app.application.interfaces import SummarizationProvider
from app.utils.exceptions import ProviderError
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are an expert summarizer. Generate a concise summary focused on key points. "
    "Do not repeat text. Target 60-80% compression. "
    "Summarize ONLY the information present. Preserve facts accurately."
)


class OpenAIProvider(SummarizationProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def summarize(self, text: str, lang: str = "en") -> str:
        try:
            # Add language instruction if available
            lang_instruction = f"Provide the summary in the same language as the text (detected as ISO code '{lang}'). "

            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"{lang_instruction}Summarize the following text. Include all key "
                                "points and important details concisely. Do not invent or "
                                "infer any information.\n\n"
                                f"{text}"
                            ),
                        },
                    ],
                    temperature=0.0,
                    max_tokens=2048,
                    top_p=1.0,
                    seed=42,
                ),
                timeout=30.0,
            )

            result = response.choices[0].message.content
            if result is None:
                raise ProviderError("openai", "Model returned empty content")
            return result.strip()

        except asyncio.TimeoutError:
            raise ProviderError("openai", "Request timed out")
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("openai", str(e))

    async def health_check(self) -> dict:
        return {
            "provider": "openai",
            "model": self._model,
            "status": "ready",
        }
