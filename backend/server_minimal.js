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

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`Chat endpoint: http://localhost:${PORT}/api/chat (POST)`);
});

module.exports = app;