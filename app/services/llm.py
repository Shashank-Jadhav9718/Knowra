import asyncio
import httpx
import google.generativeai as genai
from fastapi import HTTPException
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


def build_prompt(query: str, chunks: list[dict]) -> str:
    """
    Builds the prompt for the LLM using the provided query and retrieved chunks.
    """
    context_parts = []
    for chunk in chunks:
        # Assuming each chunk is a dictionary with a 'text' key.
        text = chunk.get("text", "")
        if text:
            context_parts.append(text)

    context = "\n---\n".join(context_parts)

    prompt = f"""You are a helpful assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say 'I don't have enough information.'

Context:
{context}

Question: {query}
Answer:"""
    return prompt

async def generate_answer(prompt: str) -> str:
    """
    Calls the configured AI Provider (Gemini or Ollama) to generate an answer based on the prompt.
    """
    try:
        if settings.AI_PROVIDER.lower() == "ollama":
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 1024
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        else:
            model = genai.GenerativeModel("gemini-2.5-flash")
            generation_config = genai.types.GenerationConfig(
                temperature=0.2, max_output_tokens=1024
            )
            response = await asyncio.to_thread(
                model.generate_content, prompt, generation_config=generation_config
            )
            return response.text
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM generation failed: {str(e)}")
