# Use a lightweight Python image for the base build
FROM python:3.10-slim-buster AS builder

# Set environment variable for Python build
ENV PYTHONUNBUFFERED 1

# Copy requirements file and install dependencies in a separate layer
WORKDIR /app/backend
COPY backend/requirements.txt .
# Use pip cache to speed up builds and limit unnecessary files
RUN pip install --no-cache-dir -r requirements.txt

# --- Final Stage: Runtime Image ---
# Use a minimal image for the final runtime environment
FROM python:3.10-slim-buster

# Copy backend files (app code)
WORKDIR /app/backend
COPY backend/ .

# Copy installed dependencies from the builder stage
# This step significantly reduces the image size by ignoring temporary build files
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Set the working directory for the application
WORKDIR /app/backend

# Set the required environment variables for the LLM and Qdrant at the image level
# Note: Actual secrets must be passed via Railway Variables
ENV QDRANT_URL=${QDRANT_URL}
ENV QDRANT_API_KEY=${QDRANT_API_KEY}
ENV HF_API_TOKEN=${HF_API_TOKEN}
ENV EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
ENV GENERATION_MODEL_NAME=HuggingFaceH4/zephyr-7b-beta
ENV COLLECTION_NAME=humanoid_robotics

# Expose the port
EXPOSE 7860

# Set the entry point to run the FastAPI application using Uvicorn
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "7860"]