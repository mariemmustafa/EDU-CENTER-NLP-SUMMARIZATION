from abc import ABC, abstractmethod


class SummarizationProvider(ABC):
    @abstractmethod
    async def summarize(self, text: str, lang: str = "en") -> str:
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        pass
