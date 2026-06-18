import asyncio
import time

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from app.application.interfaces import SummarizationProvider
from app.utils.exceptions import ProviderError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HuggingFaceProvider(SummarizationProvider):
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None
        self._tokenizer = None

    async def load_model(self):
        logger.info(f"Loading HuggingFace model: {self._model_name}")
        start = time.time()

        loop = asyncio.get_event_loop()
        self._tokenizer, self._model = await loop.run_in_executor(
            None,
            self._load,
        )

        duration = round(time.time() - start, 2)
        logger.info(f"Model loaded in {duration}s")

    def _load(self):
        try:
            tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        except Exception as e:
            logger.warning(f"Fallback tokenizer load: {e}")
            tokenizer = AutoTokenizer.from_pretrained(self._model_name, use_fast=False)
            
        model = AutoModelForSeq2SeqLM.from_pretrained(self._model_name)
        model.eval()
        return tokenizer, model

    async def summarize(self, text: str, lang: str = "en") -> str:
        if not self._model or not self._tokenizer:
            await self.load_model()
            if not self._model or not self._tokenizer:
                raise ProviderError("huggingface", "Model failed to load")

        # For HuggingFace, if the text is Arabic and the model is English-only, it might produce garbage.
        # However, the user requires us to keep the API contracts and provider logic. 
        # For a truly multilingual setup, a model like mT5 would be better.
        try:
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                None,
                self._summarize_chunk,
                text,
            )
            return summary

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("huggingface", str(e))

    def _summarize_chunk(self, text: str) -> str:
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )

        with torch.no_grad():
            summary_ids = self._model.generate(
                inputs["input_ids"],
                max_length=250,
                min_length=80,
                num_beams=5,
                length_penalty=1.0,
                early_stopping=True,
                do_sample=False,  # deterministic output
                repetition_penalty=1.3,
                no_repeat_ngram_size=3,
            )

        summary = self._tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        if not summary or not summary.strip():
            raise ProviderError("huggingface", "Model returned empty content")
        return summary

    async def health_check(self) -> dict:
        return {
            "provider": "huggingface",
            "model": self._model_name,
            "status": "ready" if self._model else "not_loaded",
        }
