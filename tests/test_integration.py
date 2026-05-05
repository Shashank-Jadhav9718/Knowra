import pytest
import io
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from reportlab.pdfgen import canvas
from sqlalchemy.future import select

from main import app
from app.db.models import Organization, QueryHistory
from app.db.session import get_db
from app.db import session as db_session_module
from tests.conftest import TestingSessionLocal, override_get_db

# Override dependency for the real app
app.dependency_overrides[get_db] = override_get_db

# Make AsyncSessionLocal use our testing session for background tasks
db_session_module.AsyncSessionLocal = TestingSessionLocal

# Enable asyncio for all tests in this file
pytestmark = pytest.mark.asyncio

def create_test_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 750, "Integration Test Document.")
    c.drawString(100, 730, "This is a test PDF for uploading and querying.")
    c.save()
    return buffer.getvalue()

@patch("app.services.retrieval.get_query_embedding")
@patch("app.services.ingestion.get_embedding")
@patch("app.services.ingestion.add_vectors")
@patch("app.services.retrieval.search_vectors")
@patch("app.api.routes.documents.remove_vectors")
@patch("app.api.routes.query.generate_answer")
async def test_end_to_end_flow(
    mock_generate_answer,
    mock_remove_vectors,
    mock_search_vectors,
    mock_add_vectors,
    mock_get_embedding,
    mock_get_query_embedding,
):
    # 5. Mocks setup
    mock_get_embedding.return_value = [0.1] * 768
    mock_get_query_embedding.return_value = [0.1] * 768
    
    def add_vectors_side_effect(org_id, vectors, chunk_ids):
        return list(range(1, len(vectors) + 1))
    mock_add_vectors.side_effect = add_vectors_side_effect
    
    mock_search_vectors.return_value = [1, 2, 3] # Will match whatever we added
    mock_generate_answer.return_value = "This is a mocked answer."
    
    # 1. Create organization (insert directly to test DB)
    org_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        org = Organization(id=org_id, name="Integration Test Org")
        session.add(org)
        await session.commit()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Register user in that org -> POST /auth/register
        register_response = await client.post(
            "/auth/register",
            json={
                "email": "integration@example.com",
                "password": "strongpassword123",
                "organization_id": str(org_id)
            }
        )
        assert register_response.status_code == 201
        
        # 3. Login -> POST /auth/login -> save token
        login_response = await client.post(
            "/auth/login",
            data={
                "username": "integration@example.com",
                "password": "strongpassword123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 4. Upload a small test PDF -> POST /documents/upload
        pdf_bytes = create_test_pdf()
        files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
        upload_response = await client.post("/documents/upload", files=files, headers=headers)
        assert upload_response.status_code == 202
        doc_id = upload_response.json()["id"]
        
        # 6. Query the document -> POST /query
        query_response = await client.post(
            "/query",
            json={"query": "What is this document about?"},
            headers=headers
        )
        assert query_response.status_code == 200
        assert query_response.json()["answer"] == "This is a mocked answer."
        
        # 7. Assert QueryHistory row was saved
        async with TestingSessionLocal() as session:
            result = await session.execute(
                select(QueryHistory).where(QueryHistory.query == "What is this document about?")
            )
            history = result.scalars().first()
            assert history is not None
            assert history.response == "This is a mocked answer."
            assert str(history.organization_id) == str(org_id)
        
        # 8. Check GET /documents returns the uploaded doc
        get_docs_response = await client.get("/documents", headers=headers)
        assert get_docs_response.status_code == 200
        docs = get_docs_response.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["id"] == doc_id
        assert docs[0]["filename"] == "test.pdf"
        
        # 9. Delete the document -> DELETE /documents/{id}
        delete_response = await client.delete(f"/documents/{doc_id}", headers=headers)
        assert delete_response.status_code == 204
        
        # 10. Assert GET /documents returns empty list
        get_docs_empty = await client.get("/documents", headers=headers)
        assert get_docs_empty.status_code == 200
        assert len(get_docs_empty.json()["documents"]) == 0
