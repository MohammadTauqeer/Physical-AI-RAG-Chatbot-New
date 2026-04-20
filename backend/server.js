const path = require('path');
const fs = require('fs');
const express = require('express');
const cors = require('cors');
require('dotenv').config();

const { GoogleGenerativeAI } = require('@google/generative-ai');
const { QdrantClient } = require('@qdrant/js-client-rest');

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const qdrantClient = new QdrantClient({
    url: process.env.QDRANT_URL,
    apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'humanoid_robotics_textbook';
const EMBEDDING_MODEL = 'text-embedding-004';
const GEMINI_MODEL = 'gemini-2.0-flash'; // Updated model

const app = express();
const PORT = process.env.PORT || 3003;

app.use(cors());
app.use(express.json());

async function initializeCollection() {
    console.log('--- Initializing Qdrant ---');
    try {
        await qdrantClient.deleteCollection(COLLECTION_NAME).catch(() => {}); 
        await qdrantClient.createCollection(COLLECTION_NAME, {
            vectors: { size: 768, distance: 'Cosine' }
        });
        console.log(`✅ Collection '${COLLECTION_NAME}' created.`);
    } catch (error) {
        console.error('❌ Qdrant Error:', error.message);
    }
}

async function generateEmbedding(text) {
    const model = genAI.getGenerativeModel({ model: EMBEDDING_MODEL });
    const result = await model.embedContent(text);
    return result.embedding.values;
}

async function ingestData() {
    const filePath = path.join(__dirname, 'data', 'chapter_text.txt');
    if (!fs.existsSync(filePath)) return console.log("⚠️ File missing at:", filePath);
    
    const text = fs.readFileSync(filePath, 'utf8');
    // Chunks thore chote rakhe hain taake precision behtar ho
    const chunks = text.match(/[\s\S]{1,800}/g) || [];
    
    console.log(`🚀 Ingesting ${chunks.length} chunks...`);
    for (let i = 0; i < chunks.length; i++) {
        const vector = await generateEmbedding(chunks[i]);
        await qdrantClient.upsert(COLLECTION_NAME, {
            points: [{ 
                id: i + 1, 
                vector, 
                payload: { text: chunks[i], source: "Textbook Chapter 1" } 
            }]
        });
    }
    console.log("✨ Data Ingested Successfully.");
}

app.post('/api/chat', async (req, res) => {
    const { query } = req.body;
    try {
        const queryVector = await generateEmbedding(query);
        const searchResults = await qdrantClient.search(COLLECTION_NAME, {
            vector: queryVector,
            limit: 3,
            with_payload: true // Payload lazmi mangwaya hai
        });

        // Context ko clean format mein laya
        const context = searchResults.map(s => s.payload.text).join('\n---\n');
        
        const model = genAI.getGenerativeModel({ model: GEMINI_MODEL });
        
        // PROMPT IMPROVED: AI ko sakhti se kaha ke context use kare
        const prompt = `
        You are a specialized AI assistant for a Humanoid Robotics textbook.
        
        CONTEXT FROM TEXTBOOK:
        ${context}
        
        USER QUESTION: 
        ${query}
        
        INSTRUCTIONS:
        1. Answer using the provided context. 
        2. If the context has the answer, start with "According to the textbook..."
        3. Keep the tone professional and educational.
        
        ANSWER:`;
        
        const result = await model.generateContent(prompt);
        const responseText = result.response.text();

        // Sources ko frontend ke liye asaan banaya
        const formattedSources = searchResults.map(s => ({
            text_preview: s.payload.text,
            source: s.payload.source
        }));

        res.json({ response: responseText, sources: formattedSources });
    } catch (error) {
        console.error('❌ Chat Error:', error.message);
        res.status(500).json({ error: "Gemini Error", details: error.message });
    }
});

app.listen(PORT, async () => {
    console.log(`🚀 Backend running on port ${PORT}`);
    await initializeCollection();
    await ingestData();
    console.log("✨ ALL SYSTEMS GO!");
});