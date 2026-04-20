import requests
import json

def test_backend_api():
    """Test the backend API to ensure it returns the right format for the frontend"""
    url = "https://hackathon-i-ai-book-rag-chatbotfina.vercel.app/api/query"

    # Test query
    payload = {
        "question": "What is physical AI?",
        "top_k": 3
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response Keys: {list(data.keys())}")
            print(f"Answer field: {data.get('answer', 'NOT FOUND')}")
            print("SUCCESS: Backend is returning the correct format with 'answer' field!")
        else:
            print(f"ERROR: Backend returned status code {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"ERROR connecting to backend: {e}")
        print("Make sure the backend server is running on https://hackathon-i-ai-book-rag-chatbotfina.vercel.app")

if __name__ == "__main__":
    test_backend_api()