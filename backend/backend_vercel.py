import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables for local development
load_dotenv()

# Configure the Gemini API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Backend Error: GOOGLE_API_KEY is not set.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/")
def home():
    return {"message": "Backend is Live"}

@app.post("/api/query")
async def process_query(request: QueryRequest):
    Q_URL = os.getenv("QDRANT_URL")
    Q_KEY = os.getenv("QDRANT_API_KEY")

    if not all([Q_URL, Q_KEY, GOOGLE_API_KEY]):
        return {"answer": "Backend Error: API keys for Qdrant or Google are missing."}

    try:
        # 1. Get Embeddings with the correct Gemini model
        embedding_result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=request.query,
            task_type="retrieval_query"
        )
        vector = embedding_result['embedding']

        # 2. Qdrant Search
        q_client = QdrantClient(url=Q_URL, api_key=Q_KEY, timeout=10)
        
        # Use search with query_vector directly
        res = q_client.query_points(
            collection_name="humanoid_robotics", 
            query_embedding=vector, 
            limit=3,
            with_payload=True
        )

        context = "\n".join([r.payload.get("text", "") for r in res.points if r.payload])

        # 3. Generate Response with Gemini Pro
        llm = genai.GenerativeModel('gemini-pro')
        prompt = f"Context: {context}\n\nQuestion: {request.query}\n\nAnswer concisely:"
        
        llm_resp = llm.generate_content(prompt)
        
        # Access the text property of the response
        answer = llm_resp.text.strip()
        
        return {"answer": answer}

    except Exception as e:
        # General error handling
        return {"answer": f"An unexpected error occurred: {str(e)}"}