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


def generate_answer(prompt: str) -> str:
    """
    Calls the Gemini API to generate an answer based on the prompt.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        generation_config = genai.types.GenerationConfig(
            temperature=0.2, max_output_tokens=1024
        )
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM generation failed: {str(e)}")
