# 🎓 AI Course Generator

An AI-powered course generation and intelligent tutoring system built with **FastAPI**, **LangGraph**, **RAG**, and **local LLMs**. Transform PDFs into interactive, personalized learning experiences with adaptive memory, quiz generation, and context-aware tutoring.

---

## ✨ Features

- 📚 **AI Course Generation** - Automatically generate structured courses from PDF documents
- 🤖 **Intelligent Chatbot** - Context-aware tutoring with LangGraph-powered agents
- 🔍 **Advanced RAG Pipeline** - Hybrid retrieval (pgvector + BM25 + RRF) with reranking
- 📝 **Quiz Generation** - Auto-generate MCQs and coding questions from course content
- 🧠 **Adaptive Learning** - Track user progress and knowledge state per concept
- 💬 **SSE Streaming** - Real-time chat responses via Server-Sent Events
- 📄 **Document Management** - Upload, process, and index PDF documents
- 🔄 **Memory System** - Multi-tier conversation memory with knowledge tracking

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client / Browser                      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   FastAPI (async)   │
              │  /chat              │
              │  /courses           │
              │  /quiz              │
              │  /documents         │
              │  /progress          │
              └─────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│  Chatbot      │ │   Course     │ │    Quiz      │
│  Agent        │ │  Generator   │ │   Engine     │
│  (LangGraph)  │ │  (LangGraph) │ │  (LangGraph) │
└───────┬───────┘ └──────┬───────┘ └──────┬───────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                  ┌──────────────┐
                  │ RAG Pipeline │
                  └──────┬───────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │ pgvector │ │  pg_bm25 │ │  Redis   │
      │ (dense)  │ │ (sparse) │ │ (cache)  │
      └────┬─────┘ └────┬─────┘ └──────────┘
           │            │
           └──────┬─────┘
                  ▼
          ┌───────────────┐
          │ RRF Fusion    │
          │ (top 20)      │
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │   Reranker    │
          │  (bge-m3)     │
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │  LLM (Qwen)   │
          │ Local/Groq    │
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │  PostgreSQL   │
          │ (history +    │
          │  progress)    │
          └───────────────┘
```

---

## 📁 Project Structure

```
ai-course-generator/
├── app/
│   ├── api/                    # REST API endpoints
│   │   ├── chat.py             # SSE streaming chat endpoint
│   │   ├── courses.py          # Course generation endpoints
│   │   ├── documents.py        # PDF upload & management
│   │   ├── health.py           # Health check endpoint
│   │   ├── progress.py         # User progress tracking
│   │   └── quiz.py             # Quiz generation endpoints
│   ├── agents/                 # LangGraph agents
│   │   ├── chatbot.py          # ReAct chatbot graph
│   │   ├── course_gen.py       # Course generation graph
│   │   └── quiz_engine.py      # Quiz generation graph
│   ├── rag/                    # RAG pipeline
│   │   ├── embedder.py         # Embedding model wrapper
│   │   ├── generator.py        # LLM generation
│   │   ├── hyde.py             # Hypothetical Document Embedding
│   │   ├── reranker.py         # bge-reranker integration
│   │   └── retriever.py        # Hybrid retrieval + RRF
│   ├── memory/                 # Memory system
│   │   ├── history.py          # Conversation history
│   │   └── knowledge.py        # User knowledge state
│   ├── indexing/               # Document indexing
│   │   └── ingest.py           # Chunk + embed + store
│   ├── adaptive/               # Adaptive learning
│   ├── db/                     # Database connections
│   │   ├── postgres.py         # Async SQLAlchemy sessions
│   │   └── redis.py            # Redis client
│   └── config.py               # Application settings
├── scripts/                    # Utility scripts
│   ├── init_db.sql             # Database initialization
│   └── test_*.py               # Test scripts
├── docker-compose.yml          # PostgreSQL + Redis services
├── requirements.txt            # Python dependencies
├── main.py                     # FastAPI application entry point
└── README.md                   # This file
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI, Python 3.10+ |
| **Database** | PostgreSQL (ParadeDB) with pgvector & pg_bm25 |
| **Cache** | Redis 7.4 |
| **AI Agents** | LangGraph 1.0.x |
| **LLM** | Qwen2.5-Coder-7B (local via vLLM) / Groq API |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2 / Qwen3-Embedding) |
| **Reranking** | FlagEmbedding (bge-reranker-v2-m3) |
| **Search** | Hybrid (pgvector cosine similarity + BM25 + RRF fusion) |
| **Containerization** | Docker & Docker Compose |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose**
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-course-generator.git
cd ai-course-generator
```

### 2. Set Up Environment

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+asyncpg://admin:your_password@localhost:5432/coursedb

# Redis
REDIS_URL=redis://localhost:6379

# Groq API (optional - for cloud LLM)
GROQ_API_KEY=your_groq_api_key

# Secret Key
SECRET_KEY=your_secret_key_here
```

### 3. Start Infrastructure

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** (ParadeDB) on port `5432`
- **Redis** on port `6379`

### 4. Initialize Database

Run the initialization script:

```bash
docker exec -i coursedb psql -U admin -d coursedb < scripts/init_db.sql
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the Application

```bash
uvicorn main:app --reload
```

The API will be available at:
- **Base URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📖 API Endpoints

### Health Check
```
GET /api/health
```

### Documents
```
POST   /api/documents/upload      # Upload PDF documents
GET    /api/documents             # List all documents
DELETE /api/documents/{id}        # Delete a document
```

### Courses
```
POST   /api/courses/generate      # Generate a course from documents
GET    /api/courses               # List user's courses
GET    /api/courses/{id}          # Get course details
DELETE /api/courses/{id}          # Delete a course
```

### Chat
```
POST   /api/chat                  # Send a message (SSE streaming)
GET    /api/chat/history          # Get conversation history
```

### Quiz
```
POST   /api/quiz/generate         # Generate quiz questions
POST   /api/quiz/submit           # Submit quiz answers
GET    /api/quiz/{id}             # Get quiz results
```

### Progress
```
GET    /api/progress              # Get user progress
POST   /api/progress/update       # Update progress
```

---

## 🔩 RAG Pipeline Explained

### 1. **Document Ingestion**
- PDFs are chunked and embedded using sentence transformers
- Chunks are stored in PostgreSQL with pgvector for similarity search
- BM25 index enables keyword-based retrieval

### 2. **Hybrid Retrieval**
Two parallel searches run on each query:
- **Dense Search** (pgvector): Finds semantically similar content via cosine similarity
- **Sparse Search** (BM25): Finds exact keyword matches
- **RRF Fusion**: Combines both rankings for optimal results

### 3. **Reranking**
- Top 60 candidates from hybrid retrieval are reranked using `bge-reranker-v2-m3`
- Returns only the top 10 most relevant chunks for generation

### 4. **Generation**
- Reranked chunks + conversation history + user knowledge state are passed to the LLM
- Supports both local LLMs (via vLLM) and cloud providers (Groq)
- Responses are streamed via SSE for real-time interaction

### 5. **HyDE (Hypothetical Document Embedding)**
- Generates a hypothetical ideal answer before searching
- Uses the hypothetical answer as the query for better recall

---

## 🧠 Memory System

The system implements multi-tier memory injection:

| Tier | Source | Purpose |
|------|--------|---------|
| **Tier 1** | Current conversation | Last 10 messages for context |
| **Tier 2** | Redis session | Fast, same-day session data |
| **Tier 3** | PostgreSQL (pgvector) | Past conversations via semantic search |
| **Tier 4** | Knowledge state | User's confidence scores per concept |

This enables truly adaptive tutoring - the system knows what you've asked before and where you struggle.

---

## 🗄️ Database Schema

PostgreSQL stores:

| Table | Purpose |
|-------|---------|
| `users` | User accounts & authentication |
| `documents` | Uploaded PDF metadata |
| `courses` | Generated course plans (week/day structure) |
| `conversations` | Chat history (all turns) |
| `embeddings` | Vector embeddings (pgvector) |
| `bm25_index` | Keyword search index (pg_bm25) |
| `quizzes` | Quiz questions & answers |
| `quiz_attempts` | User quiz attempts |
| `progress` | User progress tracking |
| `knowledge_state` | Per-concept confidence scores |
| `cache` | Semantic cache entries |
| `rag_documents` | Processed document chunks |

---

## 🧪 Testing

Run tests using pytest:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest scripts/test_db_conn.py
```

---

## ⚙️ Configuration

Key settings in `app/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `database_url` | - | PostgreSQL connection string |
| `redis_url` | - | Redis connection string |
| `embedding_model` | `qwen3-embedding` | Embedding model to use |
| `amd_llm_url` | `http://165.245.136.218:8000` | Local LLM endpoint |
| `amd_embedding_url` | `http://129.212.183.140:8000` | Embedding service URL |
| `groq_api_key` | - | Groq API key (for cloud LLM) |

---

## 🔄 Development Workflow

### Adding New Documents

1. Upload PDFs via `/api/documents/upload`
2. System automatically chunks and indexes the content
3. Documents are available for course generation and RAG queries

### Generating a Course

1. Call `/api/courses/generate` with document IDs
2. LangGraph agent analyzes content and creates structured curriculum
3. Course includes week-by-week plans, daily lessons, and quizzes

### Using the Chatbot

1. Start a conversation via `/api/chat`
2. System retrieves relevant context from your documents
3. Responses are personalized based on your progress and knowledge state
4. Streamed responses appear in real-time via SSE

---

## 📈 Performance Tips

- **Preload models**: The app preloads the reranker on startup to avoid first-request latency
- **Use Redis cache**: Frequently asked questions are cached for instant responses
- **Batch document uploads**: Upload multiple PDFs together for efficient indexing
- **Monitor embeddings**: Use the AMD embedding server for faster vector generation

---

## 🛠️ Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep coursedb

# View PostgreSQL logs
docker logs coursedb
```

### Redis Connection Issues
```bash
# Check if Redis is running
docker ps | grep coursecache

# Test Redis connection
docker exec -it coursecache redis-cli ping
```

### Model Loading Issues
- Ensure you have sufficient RAM/VRAM for embedding models
- Check that AMD service URLs are accessible
- Verify `requirements.txt` dependencies are installed

---

## 📝 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

<div align="center">

**Made with ❤️ for AI-powered education**

⭐ If you found this project helpful, please give it a star!

</div>
