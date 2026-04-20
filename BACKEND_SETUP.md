# Physical AI & Humanoid Robotics RAG Chatbot

## System Requirements

### Windows
- Docker Desktop installed and running
- Python 3.8 or higher
- Microsoft Visual C++ Redistributable for Visual Studio (2015 or later)
  - Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Git (for cloning the repository)

### macOS/Linux
- Docker installed and running
- Python 3.8 or higher
- Git (for cloning the repository)

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd physical_ai_book_with_rag_chatbot
   ```

2. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your configuration:
   ```
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_COLLECTION=humanoid_robotics
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   GEMINI_API_KEY=your_api_key_here (optional)
   ```

4. Add your textbook content to the `docs/` directory as markdown files.

5. Run the system:
   ```bash
   # On Windows
   ./run_rag_system.bat
   
   # On macOS/Linux
   chmod +x run_rag_system.sh
   ./run_rag_system.sh
   ```

## Troubleshooting

### Windows-specific issues:
- If you encounter PyTorch DLL errors, install the Microsoft Visual C++ Redistributable from: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Make sure Docker is running before starting the system

### Docker issues:
- If Qdrant container fails to start, verify Docker is running and you have proper permissions

### API Access:
- The API will be available at: https://hackathon-i-ai-book-rag-chatbotfina.vercel.app
- API documentation available at: https://hackathon-i-ai-book-rag-chatbotfina.vercel.app/docs

## Usage

1. Once the system is running, add your textbook content to the `docs/` directory as markdown files
2. The ingestion process will automatically process all markdown files in the docs directory
3. Query the system using the API endpoints or the frontend interface