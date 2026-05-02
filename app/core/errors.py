class DocumentNotFound(Exception):
    """Raised when a requested document is not found."""
    pass

class OrganizationMismatch(Exception):
    """Raised when there is a mismatch between the user's organization and the requested resource's organization."""
    pass

class EmbeddingFailed(Exception):
    """Raised when the embedding generation process fails."""
    pass

class LLMFailed(Exception):
    """Raised when the LLM generation process fails."""
    pass
