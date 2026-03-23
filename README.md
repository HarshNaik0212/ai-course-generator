# 🎓 AI Course Generator

A full-stack AI-powered course generation and tutoring system built with FastAPI, LangGraph, RAG, and local LLMs.

---

## 📁 Project Structure

```
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
```

<details>
<summary>📦 Phase 2 Additions (planned)</summary>

| File | Purpose |
|------|---------|
| `app/rag/hyde.py` | HyDE implementation |
| `app/rag/reranker.py` | bge-reranker |
| `app/indexing/raptor.py` | RAPTOR hierarchical chunking |
| `app/indexing/contextual.py` | Contextual RAG prepending |
| `app/memory/compressor.py` | Conversation summarizer |
| `app/memory/cache.py` | Semantic cache |

</details>

---

## 🏗️ System Architecture

```
Browser / Client
      │
      ▼
FastAPI (async)
/chat  /generate-course  /quiz  /progress
      │
      ├─────────────────────┬───────────────────┐
      ▼                     ▼                   ▼
CHATBOT AGENT         COURSE GENERATOR     QUIZ ENGINE
(LangGraph)           (LangGraph)          (LangGraph)
      │                     │                   │
      └─────────────────────┼───────────────────┘
                            ▼
                 RAG PIPELINE (MVP)
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
    pgvector            pg_bm25             Redis
 (dense search)      (keyword search)      (cache)
         │                  │
         └────────┬──────────┘
                  ▼
          RRF Fusion (top 20)
                  │
                  ▼
       Qwen2.5-Coder-7B (vLLM)
       Streaming response → User
                  │
                  ▼
       PostgreSQL (save history + progress)
```

---

## 🔩 Full Pipeline Explained

### ① RAPTOR Hierarchical Indexing

**What it does:** Instead of storing PDFs as flat equal-sized chunks, RAPTOR builds a 4-level tree:

```
Level 0 → raw chunks (500 words each)
Level 1 → section summary (summarizes 5–10 chunks)
Level 2 → document summary (summarizes the whole PDF)
Level 3 → course summary (summarizes all PDFs of a topic)
```

**How it helps:** A student asks *"give me an overview of deep learning"* → retrieves Level 2/3 summary. A student asks *"explain backpropagation step by step"* → retrieves Level 0 raw chunk. Without RAPTOR, both queries get the same flat chunks — broad questions get poor answers.

---

### ② Contextual RAG

**What it does:** Before embedding a chunk, Qwen 7B prepends 2–3 sentences of context:

```
BEFORE: "The gradient is computed using the chain rule..."

AFTER:  "This chunk is from Chapter 4 of Deep Learning textbook,
         explaining backpropagation mathematics.
         The gradient is computed using the chain rule..."
```

**How it helps:** When a chunk is retrieved in isolation it still makes sense. Without this, chunks like *"as explained above, this method..."* have zero meaning when pulled out of context. Anthropic found this reduces retrieval failures by 49%.

---

### ③ Embedding

**What it does:** Converts text into vectors that capture meaning. Similar meaning = similar numbers = found together in search.

| | Model | Dimensions | Status |
|---|---|---|---|
| MVP | `all-MiniLM-L6-v2` | 384 | ✅ Done |
| Phase 2 | `Qwen3-Embedding-8B` | 1024 | ⬆ Upgrading |

**How it helps:** Your PDFs have math notation, code, and technical terms. Qwen3 handles these far better than MiniLM for technical/academic content.

---

### ④ Semantic Cache

**What it does:**

| | Approach | Behaviour |
|---|---|---|
| MVP | MD5 hash | Returns cache only on character-for-character match |
| Phase 2 | Cosine similarity | Returns cache if new query is 97%+ similar in meaning |

**How it helps:** Hundreds of students will ask *"what is a neural network"* in different ways:
```
"what is a neural network?"
"explain neural networks"
"can you describe what neural nets are"
```
Phase 2 cache recognizes all 3 as the same question → returns instantly. Reduces response time from **3s → 10ms**.

---

### ⑤ 4-Tier Memory Injection

**What it does:** Before answering, injects 4 types of context into the prompt:

```
Tier 1 → current conversation (last 10 messages)
Tier 2 → Redis session data (fast, same day)
Tier 3 → past conversations from pgvector (semantic search)
Tier 4 → user knowledge state (confidence scores per concept)
```

**How it helps:** Student says *"I still don't understand this"* — the chatbot knows **what** they were discussing before and **which concepts** they struggle with (from quiz attempts). Without memory, every message starts from scratch like a new conversation.

---

### ⑥ HyDE + Query Decomposition

**What it does:**

**Query Decomposition** — breaks multi-part questions into sub-queries:
```
Student asks: "explain CNNs with Python code examples"
  → sub-q1: "what is a CNN?"
  → sub-q2: "how do CNNs work mathematically?"
  → sub-q3: "Python implementation of CNN"
Retrieves for all 3 → merges results
```

**HyDE** — generates a hypothetical ideal answer first, then searches using that:
```
Query:  "explain CNNs with Python code"
  ↓
LLM generates: "A CNN (Convolutional Neural Network) processes images by..."
  ↓
Searches using THAT as the query → better recall
```

**How it helps:** Students ask messy, multi-part questions — HyDE + decomposition handles this perfectly while basic RAG would retrieve irrelevant chunks.

---

### ⑦ Hybrid Retrieval

**What it does:** Two searches run in parallel, then combine with RRF:

```
Dense search  → finds by MEANING  (pgvector cosine similarity)
Sparse search → finds by EXACT WORDS (BM25 keyword matching)
RRF fusion    → combines both rankings
```

| | Search | Status |
|---|---|---|
| MVP | `pgvector + GIN full-text + RRF` | ✅ Done |
| Phase 2 | `pgvector + pg_bm25 + RRF` | ⬆ Upgrading |

**How it helps:** Student searches *"Adam optimizer learning rate schedule"* — dense search finds semantically related content, BM25 finds exact matches for *"Adam optimizer"*. Together they catch what either alone would miss. BM25 also ranks by term frequency and rarity — much more accurate than GIN which gives every match equal weight.

---

### ⑧ Reranker `(bge-reranker-v2-m3)`

**What it does:**
```
Hybrid retrieval returns top 60 candidates
  ↓
Reranker reads EACH candidate fully against the query
  ↓
Produces precise relevance score → returns top 10 only
```

| Stage | Method | Speed |
|---|---|---|
| Retrieval | Fast approximation (ANN search) | Fast |
| Reranker | Reads full text pair | Slow but precise |

**How it helps:** Your PDFs have 150 books worth of content. The retriever might return 60 chunks that all mention *"backpropagation"* — but only 3 actually answer the student's specific question. The reranker picks those 3 accurately. Without it, the LLM gets noisy context and gives worse answers.

---

### ⑨ Generation

**What it does:** Takes the top 10 reranked chunks + conversation history + knowledge state → generates the final answer.

| | Groq Llama 70B | Fine-tuned Qwen 7B |
|---|---|---|
| Domain knowledge | Generic | Trained on your exact textbooks |
| Response style | General | Tuned to explain like a tutor |
| Cost | API credits | Free (runs on your MI300x) |
| Latency | 300–600ms TTFT | <200ms (local, no network) |
| Privacy | Data sent to Groq | Fully on-prem |

**How it helps:** When a student asks about a specific topic, the fine-tuned model already *"knows"* that content deeply from training — RAG retrieval just provides the specific passage to ground the answer. The combination is far stronger than a generic model + RAG.

---

## 🔄 End-to-End Example

```
Student: "I keep failing the quiz on backpropagation,
          can you explain it differently with code?"
          │
          ▼
Cache check → never asked exactly this → miss
          │
          ▼
Memory injection:
  → past 3 messages: student struggled with gradients
  → knowledge state: backpropagation confidence = 0.2 (struggling)
          │
          ▼
Query decomposed into:
  → "what is backpropagation intuitively?"
  → "backpropagation mathematical steps"
  → "Python code for backpropagation"
          │
          ▼
HyDE generates ideal answer → embed it
          │
          ▼
Hybrid retrieval across 150 PDFs → top 60 chunks
          │
          ▼
Reranker filters → top 10 most relevant chunks
  (3 from deep learning textbook chapter 4,
   2 from neural networks PDF,
   1 code example chunk)
          │
          ▼
Fine-tuned Qwen 7B generates answer knowing:
  → user confidence is 0.2 (explain carefully)
  → user wants code example
  → user has seen this before (different angle needed)
          │
          ▼
Personalized, grounded, code-included explanation
saved to memory + cache
```

> Every single component is solving a real problem a student would face. Remove any one of them and the quality drops noticeably.

---

## 🗄️ What PostgreSQL Stores

| Category | Details |
|----------|---------|
| 👤 Auth | User accounts & login |
| 📚 Courses | Course plans (week/day wise) |
| 💬 Chat | Conversation history (all turns) |
| 🔢 Vectors | Vector embeddings (pgvector) |
| 🔍 Search | BM25 keyword index (pg_bm25) |
| 📝 Quizzes | Quiz questions & attempts |
| 📈 Progress | User progress & knowledge state |
| ⚡ Cache | Semantic cache queries |
| 📄 RAG | Course content chunks (RAG documents) |

---

## 🗓️ Build Plan

### Phase 1 — MVP

| Day | Focus | Tasks |
|-----|-------|-------|
| **Day 1** | Foundation | PostgreSQL + pgvector + pg_bm25, Redis, vLLM (Qwen2.5-Coder-7B), all-MiniLM-L6-v2 embedding server, DB tables, FastAPI skeleton |
| **Day 2** | RAG Core | Document ingestion pipeline, hybrid retrieval (pgvector + BM25 + RRF), basic generation, retrieval quality testing |
| **Day 3** | Chatbot Agent | LangGraph ReAct chatbot, conversation history (pgvector), SSE streaming via FastAPI, Redis exact-match cache |
| **Day 4** | Course Generator | LangGraph course generator, user profiling, week/day plan (structured JSON), quiz generator (MCQ + coding) |
| **Day 5** | Memory + Adaptive | User knowledge state (concept confidence scores), memory injection, progress tracking, adaptive plan adjustment |
| **Day 6** | Polish + Test | End-to-end testing, error handling + retries, basic frontend (Next.js or HTML), code cleanup + README |

> 🚀 **MVP DONE. Working product.**

---

### Phase 2 — Upgrades

| Upgrade | Change |
|---------|--------|
| 🧠 Model | Swap 7B → 32B |
| 🔡 Embeddings | Swap MiniLM → Qwen3-Embedding-8B |
| 📂 Indexing | Add RAPTOR hierarchical indexing |
| 📝 Chunking | Add Contextual RAG (context prepending) |
| 🔍 Retrieval | Add HyDE + Query Decomposition |
| 📊 Reranking | Add bge-reranker-v2-m3 |
| ⚡ Cache | Add Semantic Cache (cosine similarity) |
| 💾 Memory | Add 4-Tier memory with compression |
| 🚀 Inference | Add Speculative Decoding |
