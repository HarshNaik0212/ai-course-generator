ai-course-generator/
├── app/
│   ├── api/
│   │   ├── chat.py             ← SSE streaming endpoint
│   │   ├── courses.py          ← course generation endpoint
│   │   └── quiz.py             ← quiz endpoints
│   ├── agents/
│   │   ├── chatbot.py          ← LangGraph chatbot graph
│   │   ├── course_gen.py       ← LangGraph course gen graph
│   │   └── quiz_engine.py      ← LangGraph quiz graph
│   ├── rag/
│   │   ├── retriever.py        ← hybrid retrieval + RRF
│   │   ├── embedder.py         ← embedding model wrapper
│   │   └── generator.py        ← LLM generation
│   ├── memory/
│   │   ├── history.py          ← save/load conversation
│   │   └── knowledge.py        ← user knowledge state
│   ├── db/
│   │   ├── postgres.py         ← async SQLAlchemy session
│   │   └── redis.py            ← Redis client
│   ├── indexing/
│   │   └── ingest.py           ← chunk + embed + store docs
│   └── config.py
├── scripts/
│   └── init_db.sql             ← run once to create tables
├── docker-compose.yml          ← postgres + redis
├── requirements.txt
└── README.md

# Phase 2 additions:
# app/rag/hyde.py              ← HyDE implementation
# app/rag/reranker.py          ← bge-reranker
# app/indexing/raptor.py       ← RAPTOR hierarchical chunking
# app/indexing/contextual.py   ← Contextual RAG prepending
# app/memory/compressor.py     ← conversation summarizer
# app/memory/cache.py          ← semantic cache

                   [ MVP ARCHITECTURE ]
┌──────────────────────────────────────────────────────────────────┐
│                    MVP SYSTEM (Days 1-6)                         │
│                                                                  │
│  Browser / Client                                                │
│       │                                                          │
│       ▼                                                          │
│  FastAPI (async)                                                 │
│  /chat  /generate-course  /quiz  /progress                      │
│       │                                                          │
│       ├──────────────────────┬────────────────────┐             │
│       ▼                      ▼                    ▼             │
│  CHATBOT AGENT          COURSE GENERATOR      QUIZ ENGINE       │
│  (LangGraph)            (LangGraph)            (LangGraph)      │
│       │                      │                    │             │
│       └──────────────────────┼────────────────────┘             │
│                              ▼                                   │
│                   RAG PIPELINE (MVP)                             │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│    pgvector             pg_bm25              Redis               │
│  (dense search)      (keyword search)       (cache)             │
│         │                    │                                   │
│         └─────────┬──────────┘                                   │
│                   ▼                                              │
│           RRF Fusion (top 20)                                   │
│                   │                                              │
│                   ▼                                              │
│        Qwen2.5-Coder-7B (vLLM)                                  │
│        Streaming response → User                                │
│                   │                                              │
│                   ▼                                              │
│        PostgreSQL (save history + progress)                     │
└──────────────────────────────────────────────────────────────────┘





┌─────────────────────────────────────────────────────────────────┐
│                    WHEN CONTENT IS ADDED                        │
│                    (Offline / Indexing Time)                    │
├─────────────────────────────────────────────────────────────────┤
│      User Query    
            │  ---> INDEXING (runs once, offline)                   │
│           ▼                                              
│  Raw Content (PDFs, Docs, Code)                                 │
│          │                                                      │
│          ▼                                                      │
│  ① RAPTOR Hierarchical Indexing                                 │
│     Split into 4 levels: chunk→section→doc→course              │
│          │                                                      │
│          ▼                                                      │
│  ② Contextual RAG                                               │
│     LLM prepends context to each chunk before embedding        │
│          │                                                      │
│          ▼                                                      │
│     Store in pgvector (dense + BM25 sparse)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                QUERY PIPELINE (runs per message)
                    WHEN USER SENDS A MESSAGE                    │
│                    (Online / Query Time)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Query: "explain async Python with examples"              │
│          │                                                      │
│          ▼                                                      │
│  ③ Semantic Cache Check  ←─────────────────────────────┐       │
│     Similar question asked before? Return instantly    │       │
│     (Redis cosine similarity > 0.97)                   │       │
│          │ (cache miss)                                │       │
│          ▼                                             │       │
│  ④ 4-Tier Memory System                                │       │
│     Inject: past conversation + user knowledge state  │       │
│          │                                             │       │
│          ▼                                             │       │
│  ⑤ HyDE + Query Decomposition                          │       │
│     a) Break into 3 sub-questions                      │       │
│     b) Generate hypothetical answer for each          │       │
│          │                                             │       │
│          ▼                                             │       │
│     Hybrid Retrieval (pgvector + BM25)                 │       │
│     → Reranker (bge-reranker-v2-m3)                   │       │
│          │                                             │       │
│          ▼                                             │       │
│  ⑥ Speculative Decoding                                │       │
│     7B draft model guesses tokens                      │       │
│     32B model verifies → 2.5x faster response         │       │
│          │                                             │       │
│          ▼                                             │       │
│     Final Response → Save to Cache ────────────────────┘       │
│                     → Save to Memory                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘



┌───────────────────────────────────────────────────┐
│         WHAT POSTGRES STORES IN YOUR APP          │
├───────────────────────────────────────────────────┤
│  ✅ User accounts & login (auth)                  │
│  ✅ Course plans (week/day wise)                  │
│  ✅ Conversation history (all chat turns)         │
│  ✅ Vector embeddings (pgvector)                  │
│  ✅ BM25 keyword index (pg_bm25)                  │
│  ✅ Quiz questions & attempts                     │
│  ✅ User progress & knowledge state               │
│  ✅ Semantic cache queries                        │
│  ✅ Course content chunks (RAG documents)         │
└───────────────────────────────────────────────────┘







DAY 1 — Foundation
  ✅ Set up PostgreSQL + pgvector + pg_bm25
  ✅ Set up Redis
  ✅ Launch Qwen2.5-Coder-7B via vLLM (ROCm)
  ✅ Launch all-MiniLM-L6-v2 embedding server
  ✅ Create all DB tables (schema below)
  ✅ FastAPI project skeleton

DAY 2 — RAG Core
  ✅ Document ingestion pipeline (chunking + embedding)
  ✅ Hybrid retrieval (pgvector dense + pg_bm25 sparse + RRF)
  ✅ Basic generation with context
  ✅ Test retrieval quality with sample course content

DAY 3 — Chatbot Agent
  ✅ LangGraph chatbot graph (ReAct agent)
  ✅ Conversation history (save + retrieve from pgvector)
  ✅ Streaming SSE response via FastAPI
  ✅ Basic Redis cache (exact match)

DAY 4 — Course Generator
  ✅ LangGraph course generator graph
  ✅ User profiling (skill level questions)
  ✅ Week plan + day plan generation (structured JSON output)
  ✅ Quiz question generator (MCQ + coding)

DAY 5 — Memory + Adaptive
  ✅ User knowledge state (concept confidence scores)
  ✅ Memory injection into chatbot context
  ✅ Progress tracking
  ✅ Basic adaptive plan adjustment (if quiz score < 60%, add remedial)

DAY 6 — Polish + Test
  ✅ End-to-end testing of all flows
  ✅ Error handling + retries
  ✅ Basic frontend (Next.js or simple HTML)
  ✅ Code cleanup + README
  ──────────────────────────────────────
  🚀 MVP DONE. Working product.
  
POST MVP — Upgrade to Phase 2
  ⬆ Swap 7B → 32B model
  ⬆ Swap MiniLM → Qwen3-Embedding-8B
  ⬆ Add RAPTOR hierarchical indexing
  ⬆ Add Contextual RAG (context prepending)
  ⬆ Add HyDE + Query Decomposition
  ⬆ Add bge-reranker-v2-m3
  ⬆ Add Semantic Cache (cosine similarity)
  ⬆ Add 4-Tier memory with compression
  ⬆ Add Speculative Decoding