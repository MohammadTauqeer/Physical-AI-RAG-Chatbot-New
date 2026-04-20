import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
import google.generativeai as genai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables for local development at the very beginning
load_dotenv()

# Initialize SentenceTransformer model
print("DEBUG: Loading SentenceTransformer model...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Configure the Gemini API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Backend Error: GOOGLE_API_KEY is not set.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)
    # List models to see what the API key sees
    try:
        print("Available models:")
        for m in genai.list_models():
            if 'embedContent' in m.supported_generation_methods or 'generateContent' in m.supported_generation_methods:
                print(f"  {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

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
    print(f"DEBUG: Received query: {request.query}")
    Q_URL = os.getenv("QDRANT_URL")
    Q_KEY = os.getenv("QDRANT_API_KEY")

    if not all([Q_URL, Q_KEY, GOOGLE_API_KEY]):
        print("Backend Error: API keys for Qdrant or Google are missing.")
        return {"answer": "Backend Error: API keys for Qdrant or Google are missing."}

    try:
        # 1. Get Embeddings
        print("DEBUG: Generating embedding using sentence-transformers...")
        vector = model.encode(request.query).tolist()
        print(f'DEBUG: Vector created. Length: {len(vector)}')

        # 2. Qdrant Search
        print("DEBUG: Connecting to Qdrant...")
        q_client = QdrantClient(url=Q_URL, api_key=Q_KEY, timeout=10)
        print("DEBUG: Searching Qdrant...")
        
        # The syntax for q_client.query_points is correct for recent versions of qdrant-client.
        # It takes the collection name, the query vector, and returns a result object with points.
        res = q_client.query_points(
            collection_name="humanoid_robotics",
            query=vector,
            limit=3,
            with_payload=True
        )
        print(f"DEBUG: Qdrant search result: {res}")

        context = "\n".join([r.payload.get("text", "") for r in res.points if r.payload])
        print(f'DEBUG: Context retrieved. Length: {len(context)}')
        if not context:
            print("DEBUG: No context found from Qdrant search.")

        # 3. Generate Response
        print("DEBUG: Generating response from LLM...")
        llm = genai.GenerativeModel('models/gemini-flash-latest')
        prompt = f"Context: {context}\n\nQuestion: {request.query}\n\nAnswer concisely:"
        
        try:
            llm_resp = llm.generate_content(prompt)
        except Exception as e:
            if "429" in str(e):
                import time
                print("DEBUG: Quota exceeded (429). Waiting 5 seconds to retry...")
                time.sleep(5)
                llm_resp = llm.generate_content(prompt)
            else:
                raise e
        
        answer = llm_resp.text.strip()
        print(f"DEBUG: Final answer: {answer}")
        
        return {"answer": answer}

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        # General error handling
        return {"answer": f"An unexpected error occurred: {str(e)}"}