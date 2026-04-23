import pytest
import tiktoken
from app.utils.chunker import chunk_text, chunk_document

def test_normal_split():
    # Use a string large enough to guarantee multiple chunks
    text = "hello world " * 500  # Will be > 1000 tokens
    
    encoder = tiktoken.get_encoding("cl100k_base")
    total_tokens = len(encoder.encode(text))
    
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    
    assert len(chunks) > 1
    # First chunk should have exactly chunk_size tokens
    assert len(encoder.encode(chunks[0])) == 400

def test_overlap_correctness():
    # Generate distinct words to ensure sequences match correctly
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    
    assert len(chunks) >= 2
    
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens_0 = encoder.encode(chunks[0])
    tokens_1 = encoder.encode(chunks[1])
    
    # Overlap means the last 50 tokens of chunk N match the first 50 tokens of chunk N+1
    assert tokens_0[-50:] == tokens_1[:50]

def test_short_text_edge_case():
    encoder = tiktoken.get_encoding("cl100k_base")
    
    # 1. Text that produces fewer than 50 tokens should be skipped entirely
    short_text = "hello world"
    assert len(encoder.encode(short_text)) < 50
    chunks = chunk_text(short_text, chunk_size=400, overlap=50)
    assert len(chunks) == 0  # Skipped because < 50 tokens
    
    # 2. Text that produces exactly 50 tokens should be kept
    tokens_50 = [encoder.encode("hello")[0]] * 50
    text_50 = encoder.decode(tokens_50)
    
    chunks_50 = chunk_text(text_50, chunk_size=400, overlap=50)
    assert len(chunks_50) == 1
    assert len(encoder.encode(chunks_50[0])) == 50

def test_chunk_document():
    # Test joining pages with double newlines and then chunking
    pages = ["First page text.", "Second page text."]
    
    # Since this combined text is short (< 50 tokens), it should return 0 chunks
    chunks_short = chunk_document(pages, chunk_size=400, overlap=50)
    assert len(chunks_short) == 0
    
    # Create longer pages to hit the >= 50 token requirement
    long_pages = ["word " * 30, "word " * 30]
    chunks_long = chunk_document(long_pages, chunk_size=400, overlap=50)
    assert len(chunks_long) >= 1
    assert "\n\n" in chunks_long[0]
