# Knowra: Multi-Tenant RAG Backend API
> A production-grade Multi-Tenant Retrieval-Augmented Generation (RAG) API built with FastAPI, PostgreSQL, FAISS, and Google Gemini API.

## Architecture Overview

```text
           +-----------------+
           |   User/Client   |
           +--------+--------+
                    | (REST API)
           +--------v--------+
           |   FastAPI App   |
           +---+---------+---+
               |         |
      +--------v-+     +-v----------+
      | Postgres |     |   FAISS    |
      | (Users,  |     | (Vectors,  |
      |  Docs,   |     |  Index by  |
      |  Query   |     |  Org ID)   |
      | History) |     +------------+
      +----------+          |
               +------------v------------+
               |    Google Gemini API    |
               | (Embeddings & LLM Gen)  |
               +-------------------------+
```

## Tech Stack

| Component | Technology | Purpose |
| --- | --- | --- |
| **Framework** | FastAPI | High-performance async REST API, dependency injection, OpenAPI docs. |
| **Database** | PostgreSQL + SQLAlchemy | Relational data persistence (Users, Organizations, Auth, Query History). |
| **Vector Store** | FAISS | Fast, efficient similarity search for document embeddings. |
| **LLM & Embeddings** | Google Gemini API | Generating vector embeddings and LLM responses via Q&A. |
| **Authentication** | OAuth2 + JWT | Secure, stateless multi-tenant authentication. |
| **Background Jobs** | FastAPI BackgroundTasks | Async document ingestion and chunking without blocking the main thread. |

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/knowra.git
   cd knowra
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your specific GEMINI_API_KEY
   ```

3. **Start the application**
   ```bash
   docker-compose up --build -d
   ```

## API Reference

| Method | Route | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | None | Register a new user and assign them to an organization. |
| `POST` | `/auth/login` | None | Authenticate and retrieve a JWT Bearer token. |
| `POST` | `/documents/upload` | User | Upload a PDF document (Max 10MB) to the organization's tenant. |
| `GET` | `/documents` | User | Retrieve all documents uploaded by the current organization. |
| `DELETE` | `/documents/{id}` | User | Delete a specific document and its associated vector chunks. |
| `POST` | `/query` | User | Submit a natural language query against the organization's documents. |
| `GET` | `/admin/users` | Admin | Retrieve all users within the admin's organization. |
| `GET` | `/admin/logs` | Admin | View recent query logs and responses across the organization. |
| `GET` | `/admin/stats` | Admin | Get usage statistics (documents, chunks, total queries). |

*(Note: The system currently uses these 9 core endpoints to cover all auth, admin, and RAG logic)*

## How It Works

### Upload Pipeline
1. **Validation & Storage**: The API validates the uploaded file (PDF only, <10MB) and saves it to a tenant-specific directory on disk.
2. **Text Extraction**: A background task extracts raw text from the PDF using PyMuPDF (`fitz`).
3. **Chunking**: Extracted text is split into smaller, semantically meaningful chunks to maintain context window limits.
4. **Embedding Generation**: The Google Gemini API converts each text chunk into high-dimensional vector embeddings (`models/text-embedding-004`).
5. **Storage & Indexing**: The vectors are inserted into FAISS (mapped to the organization), and the chunk metadata is saved to PostgreSQL to enable relational joins.

### Query Pipeline
1. **Query Embedding**: The user's natural language query is converted into a vector embedding via Gemini API.
2. **Vector Similarity Search**: FAISS performs a Nearest Neighbor (k-NN) search to find the most relevant chunk IDs.
3. **Tenant Isolation Check**: The retrieved chunk IDs are cross-referenced in PostgreSQL to guarantee they belong to the requesting user's organization.
4. **Context Assembly**: The text from the validated chunks is stitched together to form the prompt context.
5. **LLM Generation**: The enriched prompt is sent to Google Gemini API (`gemini-1.5-pro`) to generate an accurate answer based strictly on the context.
6. **Auditing**: The original query, context sources, and LLM response are logged to the `QueryHistory` table for admin oversight.

## Multi-Tenancy Strategy

Our multi-tenant architecture relies on a **Logical Isolation Strategy**:
- **Vector Store (FAISS)**: FAISS does not natively support tenant partitioning. We implement multi-tenancy by using a separate FAISS index file on disk for each `organization_id`. The vector search service dynamically loads the appropriate index during retrieval.
- **Relational DB (PostgreSQL)**: Every table (`User`, `Document`, `Chunk`, `QueryHistory`) contains an `organization_id` foreign key. The FastAPI Dependency Injection system automatically injects the current user's `organization_id` into database queries, enforcing strict row-level isolation and preventing cross-tenant data leaks.

## Environment Variables

| Variable | Description |
| --- | --- |
| `API_V1_STR` | Base API path (e.g., `/api/v1`) |
| `PROJECT_NAME` | Name of the project (e.g., `Multi-Tenant RAG API`) |
| `SECRET_KEY` | Cryptographic key used to sign JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiration time for JWTs (e.g., `1440` for 24h) |
| `POSTGRES_SERVER` | Postgres host address |
| `POSTGRES_USER` | Postgres database user |
| `POSTGRES_PASSWORD` | Postgres database password |
| `POSTGRES_DB` | Name of the Postgres database |
| `POSTGRES_PORT` | Port for the Postgres database (e.g., `5432`) |
| `DATABASE_URL` | Full connection string for SQLAlchemy |
| `GEMINI_API_KEY` | API key for Google Gemini (Embeddings & LLM) |
| `FAISS_INDEX_PATH` | Directory to store the persistent FAISS indexes |
| `LOG_LEVEL` | Application logging level (e.g., `INFO`) |

## Running Tests

The project uses `pytest` and `httpx` for comprehensive, asynchronous integration testing. To run the test suite locally:

```bash
export PYTHONPATH=.
pytest tests/
```

## Deployment

To deploy this application to **Render**:
1. **Connect Repository**: Create a new "Web Service" on Render and connect your GitHub repository.
2. **Environment Configuration**: Set the Build Command to `pip install -r requirements.txt` and the Start Command to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. **Database Setup**: Create a Render PostgreSQL database and copy the "Internal Database URL".
4. **Environment Variables**: In the Web Service settings, add the Environment Variables matching your `.env` file (paste the DB URL into `DATABASE_URL`). Include your `GEMINI_API_KEY`.
5. **Disk Storage**: Attach a Persistent Disk to the service (mounted at `./data/faiss_index` and `./uploads`) so FAISS indices and PDFs survive stateless container deployments.
6. **Deploy**: Trigger a manual deploy or push to the main branch.

## Tradeoffs & Design Decisions

- **FAISS vs. pgvector**: We chose FAISS for high-performance, in-memory vector similarity search which is extremely fast for small-to-medium datasets. `pgvector` would simplify architecture by keeping vectors in Postgres, but FAISS avoids heavy DB compute overhead at the cost of managing separate disk indices (which require persistent volume claims in deployment).
- **Chunk Size Choices**: Documents are split into semantic chunks. Larger chunks provide more context for the LLM but dilute embedding accuracy. Smaller chunks yield precise search results but may cut off important contextual sentences. We opted for balanced chunking to maximize retrieval relevance without losing context.
- **Google Gemini API vs. Local LLMs**: By utilizing the Gemini API, we offload massive compute requirements, resulting in lower infrastructure costs and incredibly fast inference times. A local open-source LLM (like Llama 3) would provide maximum privacy and no vendor lock-in, but requires expensive GPU hosting and brings higher latency.
