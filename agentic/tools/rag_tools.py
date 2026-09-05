import os
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
from sqlalchemy import create_engine
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from utils import get_session
from data.models.udahub import Knowledge, Ticket
from dotenv import load_dotenv


load_dotenv()
udahub_db = "data/core/udahub.db"
engine = create_engine(f"sqlite:///{udahub_db}", echo=False)

embeddings_fn = OpenAIEmbeddings(
    model="text-embedding-3-large",
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

KB_COLLECTION = "udahubassistant"
KB_PERSIST_DIR = "./cultpass_knowledge_base"

HISTORY_COLLECTION = "udahubtickets"
HISTORY_PERSIST_DIR = "./udahub_tickets_knowledge_base"


def build_knowledge_index():
    """Builds the Knowledge base"""
    vector_store = Chroma(
        collection_name=KB_COLLECTION,
        embedding_function=embeddings_fn,
        persist_directory=KB_PERSIST_DIR,
    )

    documents = []
    with get_session(engine) as session:
        knowledge = session.query(Knowledge).all()
        if len(knowledge) == 0:
            return [{"error": "No information found"}]

        for article in knowledge:
            doc = Document(
                page_content=article.content,
                metadata={"title": article.title, "tags": article.tags},
                id=article.article_id,
            )
            documents.append(doc)

    vector_store.add_documents(documents=documents)
    return "Successfully saved to Knowledge base!"


def search_knowledge_base(query: str) -> list[dict]:
    """Queries the Knowledge Base, returning relevant article, content information"""
    vector_store = Chroma(
        collection_name=KB_COLLECTION,
        embedding_function=embeddings_fn,
        persist_directory=KB_PERSIST_DIR,
    )

    documents = vector_store.similarity_search(query, k=5)
    result = []
    for doc in documents:
        result.append({
            "title": doc.metadata["title"],
            "content": doc.page_content,
            "tags": doc.metadata.get("tags"),
            "id": doc.id,
        })
    return result


def build_user_history_index():
    """Builds the per-user ticket history index"""
    vector_store = Chroma(
        collection_name=HISTORY_COLLECTION,
        embedding_function=embeddings_fn,
        persist_directory=HISTORY_PERSIST_DIR,
    )

    documents = []
    with get_session(engine) as session:
        tickets = session.query(Ticket).all()
        if len(tickets) == 0:
            return "No information to add!"

        for ticket in tickets:
            cultpass_user_id = ticket.user.external_user_id
            user_messages = [msg for msg in ticket.messages if msg.role.value == "user"]
            ai_messages = [msg for msg in ticket.messages if msg.role.value == "ai"]
            if len(user_messages) == 0 or len(ai_messages) == 0:
                continue

            question = user_messages[0].content
            answer = ai_messages[0].content
            doc = Document(
                page_content=f"Q: {question}\nA: {answer}",
                metadata={"user_id": cultpass_user_id, "ticket_id": ticket.ticket_id},
                id=ticket.ticket_id,
            )
            documents.append(doc)

    if len(documents) == 0:
        return "No complete question/answer pairs found to index."

    vector_store.add_documents(documents)
    return "Successfully saved to Knowledge base!"


def fetch_user_history(user_id: str, query: str) -> list[Document]:
    """Semantic search over this user's past ticket history. Returns an
    empty list if nothing sufficiently relevant is found."""
    vector_store = Chroma(
        collection_name=HISTORY_COLLECTION,
        embedding_function=embeddings_fn,
        persist_directory=HISTORY_PERSIST_DIR,
    )

    documents = vector_store.similarity_search(query, k=5, filter={"user_id": user_id})
    return documents if len(documents) > 0 else []