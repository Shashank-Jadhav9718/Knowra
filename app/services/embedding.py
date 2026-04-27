import time
import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure the API key for Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

def _get_embedding_with_retry(text: str, task_type: str) -> list[float]:
    max_attempts = 3
    base_delay = 1
    
    for attempt in range(max_attempts):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type=task_type
            )
            return result['embedding']
        except Exception as e:
            if attempt == max_attempts - 1:
                logger.error(f"Failed to get embedding after {max_attempts} attempts: {e}")
                raise e
            
            sleep_time = base_delay * (2 ** attempt)
            logger.warning(
                f"Error getting embedding (attempt {attempt + 1}/{max_attempts}): {e}. "
                f"Retrying in {sleep_time}s..."
            )
            time.sleep(sleep_time)

def get_embedding(text: str) -> list[float]:
    """
    Get embedding for a document using models/text-embedding-004.
    """
    return _get_embedding_with_retry(text, task_type="retrieval_document")

def get_query_embedding(text: str) -> list[float]:
    """
    Get embedding for a search query using models/text-embedding-004.
    """
    return _get_embedding_with_retry(text, task_type="retrieval_query")
