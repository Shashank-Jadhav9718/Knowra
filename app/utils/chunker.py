import tiktoken

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Split text into chunks of `chunk_size` tokens with `overlap` tokens between consecutive chunks.
    Chunks with fewer than 50 tokens are skipped.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be strictly less than chunk_size")
        
    if not text.strip():
        return []
        
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(text)
    
    chunks = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i:i + chunk_size]
        
        # Skip chunks under 50 tokens
        if len(chunk_tokens) >= 50:
            chunks.append(encoder.decode(chunk_tokens))
            
        # Break if we have reached the end of the tokens array
        if i + chunk_size >= len(tokens):
            break
            
        # Advance by chunk_size - overlap to ensure the correct overlap
        i += (chunk_size - overlap)
        
    return chunks

def chunk_document(pages: list[str], chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Join a list of pages with double newlines and chunk the resulting text.
    """
    joined_text = "\n\n".join(pages)
    return chunk_text(joined_text, chunk_size=chunk_size, overlap=overlap)
