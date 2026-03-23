from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypedDict, List, Annotated
from app.rag.retriever import hybrid_retrieve
from app.rag.generator import get_llm, build_rag_prompt
from app.memory.history import get_recent_history, save_message
import operator

# ── State ──────────────────────────────────────────────────
class ChatState(TypedDict):
    user_id: str
    session_id: str
    question: str
    context_chunks: List[dict]
    conversation_history: List[dict]
    answer: str
    db: object                        # AsyncSession passed through state

# ── Node 1: Load conversation history ──────────────────────
async def load_history_node(state: ChatState) -> dict:
    history = await get_recent_history(
        db=state["db"],
        session_id=state["session_id"],
        limit=10
    )
    return {"conversation_history": history}

# ── Node 2: Retrieve relevant chunks ───────────────────────
async def retrieve_node(state: ChatState) -> dict:
    chunks = await hybrid_retrieve(
        db=state["db"],
        query=state["question"],
        top_k=5
    )
    return {"context_chunks": chunks}

# ── Node 3: Generate answer ─────────────────────────────────
async def generate_node(state: ChatState) -> dict:
    llm = get_llm(streaming=False)

    prompt = build_rag_prompt(
        question=state["question"],
        context_chunks=state["context_chunks"],
        conversation_history=state["conversation_history"]
    )

    response = await llm.ainvoke(prompt)
    answer = response.content
    return {"answer": answer}

# ── Node 4: Save to memory ──────────────────────────────────
async def save_memory_node(state: ChatState) -> dict:
    # Save user message
    await save_message(
        db=state["db"],
        user_id=state["user_id"],
        session_id=state["session_id"],
        role="user",
        content=state["question"]
    )
    # Save assistant answer
    await save_message(
        db=state["db"],
        user_id=state["user_id"],
        session_id=state["session_id"],
        role="assistant",
        content=state["answer"]
    )
    return {}

# ── Build Graph ─────────────────────────────────────────────
def build_chatbot_graph():
    graph = StateGraph(ChatState)

    graph.add_node("load_history", load_history_node)
    graph.add_node("retrieve",     retrieve_node)
    graph.add_node("generate",     generate_node)
    graph.add_node("save_memory",  save_memory_node)

    graph.set_entry_point("load_history")
    graph.add_edge("load_history", "retrieve")
    graph.add_edge("retrieve",     "generate")
    graph.add_edge("generate",     "save_memory")
    graph.add_edge("save_memory",  END)

    return graph.compile()

chatbot_graph = build_chatbot_graph()