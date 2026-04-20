import os
from dotenv import load_dotenv
from dotenv import dotenv_values
import logging
from typing import Dict, List, Optional

# Load environment variables
config = dotenv_values(".env")
if not config:
    config = os.environ

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import after loading env vars to avoid circular import issues
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from huggingface_hub import InferenceClient
import uvicorn

from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Physical AI & Humanoid Robotics RAG Chatbot API",
    description="API for querying Physical AI & Humanoid Robotics textbook content using Retrieval Augmented Generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration constants
COLLECTION_NAME = config['COLLECTION_NAME']
QDRANT_URL = config['QDRANT_URL']
QDRANT_API_KEY = config['QDRANT_API_KEY']
HF_API_TOKEN = config['HF_API_TOKEN']
EMBEDDING_MODEL_NAME = config['EMBEDDING_MODEL_NAME']
GENERATION_MODEL_NAME = config['GENERATION_MODEL_NAME']

# Global variables for clients
qdrant_client: Optional[QdrantClient] = None
embeddings: Optional[HuggingFaceEmbeddings] = None
qdrant_vector_store: Optional[QdrantVectorStore] = None
hf_client: Optional[InferenceClient] = None


class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    question: str
    top_k: int = 3


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    answer: str
    sources: List[Dict[str, str]]
    question: str


@app.on_event("startup")
def startup_event():
    """Initialize clients when the application starts"""
    global qdrant_client, embeddings, qdrant_vector_store, hf_client

    logger.info("Initializing HuggingFace embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name=config["EMBEDDING_MODEL_NAME"]
    )

    logger.info("Initializing Qdrant client for cloud...")
    qdrant_client = QdrantClient(
        url=config["QDRANT_URL"],
        api_key=config["QDRANT_API_KEY"],
        https=True  # Ensuring HTTPS for cloud connection
    )

    logger.info("Initializing Qdrant vector store...")
    qdrant_vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=config["COLLECTION_NAME"],
        embedding=embeddings,  # Fixed: changed from 'embeddings' to 'embedding'
    )

    # Initialize the Hugging Face client
    logger.info("Initializing Hugging Face client...")
    hf_client = InferenceClient(
        model=config['GENERATION_MODEL_NAME'],
        token=config['HF_API_TOKEN']
    )

    # Check if collection exists
    try:
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]

        if config["COLLECTION_NAME"] not in collection_names:
            logger.warning(f"Collection '{config['COLLECTION_NAME']}' does not exist. Please make sure to run the ingestion script first.")
        else:
            logger.info(f"Connected to collection '{config['COLLECTION_NAME']}' successfully.")

            # Verify collection has vectors by checking count
            try:
                count = qdrant_client.count(collection_name=config["COLLECTION_NAME"])
                logger.info(f"Collection '{config['COLLECTION_NAME']}' has {count.count} vectors")
                if count.count == 0:
                    logger.warning(f"Collection '{config['COLLECTION_NAME']}' exists but has 0 vectors. Re-run ingestion script.")
            except Exception as e:
                logger.error(f"Error getting vector count: {str(e)}")

    except Exception as e:
        logger.error(f"Error connecting to Qdrant: {str(e)}")
        raise


def retrieve_chunks(question: str, top_k: int) -> List[Dict]:
    """Retrieve relevant chunks from Qdrant vector store."""
    if qdrant_vector_store is None:
        raise HTTPException(status_code=500, detail="Qdrant vector store not initialized.")

    # Retrieval method: Simple similarity search
    retrieved_docs = qdrant_vector_store.similarity_search(question, k=top_k)

    # Convert documents to required format
    sources = []
    for doc in retrieved_docs:
        sources.append({
            "text": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "relevance_score": "N/A"
        })
    return sources


@app.get("/")
def read_root():
    """Root endpoint for health check"""
    return {"message": "Physical AI & Humanoid Robotics RAG Chatbot API is running", "status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    """
    Query endpoint that takes a question and returns an answer based only on the book content
    """
    try:
        # Validate inputs
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        if request.top_k <= 0 or request.top_k > 10:
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 10")

        logger.info(f"Processing query: '{request.question[:50]}...' with top_k={request.top_k}")

        # Retrieve relevant chunks from the vector store
        sources = retrieve_chunks(request.question, request.top_k)

        if not sources:
            raise HTTPException(status_code=404, detail="No relevant content found in the textbook")

        # Combine the context from retrieved sources
        context_parts = [source["text"] for source in sources]
        context = "\n\n".join(context_parts)

        # Format the prompt for the LLM with context and question
        prompt = f"""
        Based on the following context from the Physical AI & Humanoid Robotics textbook, please answer the question.

        Context:
        {context}

        Question: {request.question}

        Answer:
        """

        # Generate response using the Hugging Face client
        if hf_client is None:
            raise HTTPException(status_code=500, detail="Hugging Face client not initialized")

        response = hf_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512
        )
        answer = response.choices[0].message.content

        response = QueryResponse(
            answer=answer,
            sources=sources,
            question=request.question
        )

        logger.info(f"Query processed successfully. Found {len(sources)} source documents.")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RAG Chatbot API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)