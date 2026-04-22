import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Config
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "humanoid_robotics" 

genai.configure(api_key=API_KEY)
q_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# --- STARTUP DIAGNOSTICS ---
logger.info("🔍 Checking available models...")
try:
    models = genai.list_models()
    logger.info("✅ Available Models for your API Key:")
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            logger.info(f"👉 {m.name}")
except Exception as e:
    logger.error(f"❌ Could not list models: {e}")

class QueryRequest(BaseModel):
    question: str

def get_embedding(text: str):
    try:
        # Aapke terminal ke mutabiq ye model 100% available hai
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_query",
            output_dimensionality=384
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"❌ Embedding Error: {str(e)}")
        raise e

@app.post("/api/query")
async def chat_handler(request: QueryRequest):
    try:
        logger.info(f"🚀 Processing: {request.question}")
        query_vector = get_embedding(request.question)

        search_results = q_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=3
        ).points

        context_list = [res.payload.get('text') or res.payload.get('content') or "" for res in search_results]
        context = "\n---\n".join(filter(None, context_list)) or "No textbook context found."
        
# --- BALANCED EXPERT PROMPT ---
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        You are an expert Professor specialized in 'Physical AI & Humanoid Robotics'. 
        Your task is to provide helpful and technical answers based on the textbook context provided below.

        RULES:
        1. If the question is about Robotics, AI, Sensors, or any technical topic, answer it thoroughly using the context.
        2. Even if the context is brief, use your expertise to explain it simply but keep it grounded in the textbook's theme.
        3. If (and ONLY if) the question is completely unrelated (like food, recipes, celebrities, or general gossip), politely say: 
           "Sorry, this question is not strictly related to the robotics textbook."

        Context:
        {context}

        User Question: 
        {request.question}

        Answer:"""
        
        llm_response = model.generate_content(prompt)
        
        return {"response": llm_response.text}

    except Exception as e:
        logger.error(f"❌ API Error: {str(e)}")
        # Check if it's a 404 for model name
        if "404" in str(e):
            return {"response": f"Model name mismatch. Please check terminal for available models list."}
        return {"response": f"Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)