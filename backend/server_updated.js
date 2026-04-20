const path = require('path');
const fs = require('fs');
const express = require('express');
const cors = require('cors');
require('dotenv').config();
const { GoogleGenAI } = require('@google/genai');
const { QdrantClient } = require('@qdrant/js-client-rest');

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const COLLECTION_NAME = 'humanoid_robotics_textbook';
const EMBEDDING_MODEL = 'text-embedding-004'; // Using Gemini's text-embedding-004 model

// Initialize Qdrant client with cloud configuration
const qdrantClient = new QdrantClient({
    url: process.env.QDRANT_URL,
    apiKey: process.env.QDRANT_API_KEY,
});

// Text splitting function to divide the book content into chunks
function splitTextIntoChunks(text, chunkSize = 1000, overlap = 200) {
    const chunks = [];
    let i = 0;
    while (i < text.length) {
        let end = Math.min(i + chunkSize, text.length);
        if (end < text.length) {
            let lastSpace = text.lastIndexOf(' ', end);
            if (lastSpace > i) {
                end = lastSpace;
            }
        }
        chunks.push(text.substring(i, end));
        i = end - overlap;
    }
    return chunks;
}

// Ingestion function to read the book, create embeddings, and store in Qdrant Cloud
async function ingestData() {
    console.log('--- Starting Data Ingestion Process ---');

    try {
        // Verify connection to Qdrant Cloud
        await qdrantClient.getCollections();
        console.log("Qdrant Cloud Connection: SUCCESSFUL");

        // Define the path to the book file
        const filePath = path.join(__dirname, 'data', 'chapter_text.txt');

        // Check if data directory exists, create if not
        const dataDir = path.join(__dirname, 'data');
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
            console.log("Created data directory");
        }

        // Check if the book file exists
        if (!fs.existsSync(filePath)) {
            console.error(`Error: Data file not found at ${filePath}. Please ensure chapter_text.txt is in the data folder.`);
            
            // Try to copy from frontend/data if it exists
            const frontendFilePath = path.join(__dirname, '..', 'frontend', 'data', 'chapter_text.txt');
            if (fs.existsSync(frontendFilePath)) {
                fs.copyFileSync(frontendFilePath, filePath);
                console.log("Copied chapter_text.txt from frontend/data to backend/data");
            } else {
                console.error("chapter_text.txt not found in either backend/data or frontend/data");
                return;
            }
        }

        const fileContent = fs.readFileSync(filePath, 'utf8');

        // 1. Split the text into chunks
        const chunks = splitTextIntoChunks(fileContent);
        console.log(`Split file into ${chunks.length} chunks.`);

        // 2. Check if collection exists, create if not
        const collections = await qdrantClient.getCollections();
        const collectionExists = collections.collections.some(
            (c) => c.name === COLLECTION_NAME
        );

        if (!collectionExists) {
            console.log(`Creating collection: ${COLLECTION_NAME}`);
            // Create collection with 768-dimensional vectors (for text-embedding-004)
            await qdrantClient.createCollection(COLLECTION_NAME, {
                vectors: { size: 768, distance: 'Cosine' },
            });
            console.log('Collection created successfully.');
        } else {
            console.log('Collection exists. Clearing existing points for fresh ingest.');
            // Clear existing points for a clean ingest
            await qdrantClient.delete(COLLECTION_NAME, {
                points_selector: { filter: {} },
            });
        }

        // 3. Create embeddings and prepare points for Qdrant
        const points = [];
        for (let i = 0; i < chunks.length; i++) {
            const chunk = chunks[i];

            // Create embedding using Gemini's text-embedding-004
            const embeddingResult = await ai.embedContent({
                model: `models/${EMBEDDING_MODEL}`,
                content: { parts: [{ text: chunk }] },
                taskType: "RETRIEVAL_DOCUMENT",
            });

            const vector = embeddingResult.embedding.values;

            points.push({
                id: i + 1,
                vector: vector,
                payload: {
                    text: chunk,
                    chapter: '1. Introduction to Humanoid Robotics',
                    chunk_index: i,
                },
            });

            console.log(`Generated embedding for chunk ${i + 1}/${chunks.length}`);
        }

        // 4. Upload points to Qdrant in batches
        const batchSize = 50; // Process in batches to avoid timeouts
        for (let i = 0; i < points.length; i += batchSize) {
            const batch = points.slice(i, i + batchSize);
            await qdrantClient.upsert(COLLECTION_NAME, {
                wait: true,
                points: batch,
            });
            console.log(`Uploaded batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(points.length / batchSize)}`);
        }

        console.log(`--- Data Ingestion Complete! Added ${points.length} points to Qdrant Cloud ---`);

    } catch (error) {
        console.error('Data Ingestion Failed:', error.message);
        console.error('Check 1: Are your QDRANT_URL and QDRANT_API_KEY correct in the .env file?');
        console.error('Check 2: Is your GEMINI_API_KEY valid in the .env file?');
        console.error('Check 3: Does the data/chapter_text.txt file exist?');
    }
}

const app = express();
const PORT = process.env.PORT || 3003;

// Middleware
app.use(cors({
    origin: '*',
    credentials: true,
    optionsSuccessStatus: 200
}));
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'OK', message: 'Server is running and connected to Qdrant Cloud' });
});

// Chat endpoint for RAG functionality
app.post('/api/chat', async (req, res) => {
    const { query } = req.body;
    
    if (!query) {
        return res.status(400).json({ error: 'Query is required' });
    }
    
    console.log(`Received query for RAG: ${query}`);

    try {
        // Create embedding for the user's query
        const embeddingResult = await ai.embedContent({
            model: `models/${EMBEDDING_MODEL}`,
            content: { parts: [{ text: query }] },
            taskType: "RETRIEVAL_QUERY",
        });

        const queryVector = embeddingResult.embedding.values;

        // Search Qdrant Cloud for the top 3 most relevant chunks
        const searchResults = await qdrantClient.search(COLLECTION_NAME, {
            vector: queryVector,
            limit: 3, // Get top 3 most relevant chunks
            with_payload: true,
        });

        // Extract the text content from search results
        const relevantChunks = searchResults.map(result => result.payload.text);
        
        // Format context from retrieved chunks
        const context = relevantChunks.join('\n\n---\n\n');

        // Construct the prompt for Gemini with the retrieved context
        const fullPrompt = `Based on the following context, please answer the question. If the context doesn't contain enough information, say so.\n\nContext:\n${context}\n\nQuestion: ${query}\n\nAnswer:`;

        // Send the context + question to Gemini (gemini-2.0-flash) to get the final answer
        const model = ai.getGenerativeModel({ model: "gemini-2.0-flash" });
        const result = await model.generateContent(fullPrompt);
        const response = await result.response.text();

        // Send the response in the required format
        res.json({
            response: response
        });
    } catch (error) {
        console.error('Error processing chat query:', error);
        res.status(500).json({ error: 'Failed to process chat query' });
    }
});

// Trigger data ingestion when the server starts
ingestData().then(() => {
    // Start the server only after ingestion is complete
    app.listen(PORT, () => {
        console.log(`Server is running on port ${PORT}`);
        console.log(`Health check: http://localhost:${PORT}/health`);
        console.log(`Chat endpoint: http://localhost:${PORT}/api/chat (POST)`);
    });
});

module.exports = app;