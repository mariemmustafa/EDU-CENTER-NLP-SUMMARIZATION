import asyncio
import sys

from app.infrastructure.providers.huggingface_provider import HuggingFaceProvider
from app.services.summarization_service import SummarizationService

async def test_summarization():
    print("Initializing HuggingFace Provider (this may take a moment to load the model)...")
    # Using the default model typically used in this codebase, let's use a small one or whatever is default
    # But since I don't know the default, let's just initialize the service via dependencies if possible.
    from app.dependencies import initialize_dependencies
    from app.dependencies import get_use_case
    
    await initialize_dependencies()
    print("Dependencies initialized.")
    use_case = get_use_case()
    
    # We can test the underlying summarization_service directly
    service = use_case._summarization_service
    
    english_text = "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals including humans. Leading AI textbooks define the field as the study of intelligent agents: any system that perceives its environment and takes actions that maximize its chance of achieving its goals. Some popular accounts use the term artificial intelligence to describe machines that mimic cognitive functions that humans associate with the human mind, such as learning and problem solving. " * 5
    
    print("Testing English text summarization...")
    en_summary = await service.summarize(text=english_text, lang="en")
    print(f"English Summary: {en_summary}\n")
    
    arabic_text = "الذكاء الاصطناعي هو سلوك وخصائص معينة تتسم بها البرامج الحاسوبية تجعلها تحاكي القدرات الذهنية البشرية وأنماط عملها. من أهم هذه الخاصيات القدرة على التعلم والاستنتاج ورد الفعل على أوضاع لم تبرمج في الآلة. " * 5
    print("Testing Arabic text summarization...")
    ar_summary = await service.summarize(text=arabic_text, lang="ar")
    print(f"Arabic Summary: {ar_summary}\n")
    print("Verification completed successfully.")

if __name__ == "__main__":
    asyncio.run(test_summarization())
