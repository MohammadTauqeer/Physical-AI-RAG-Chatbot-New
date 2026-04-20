import requests
import json

def test_query_endpoint():
    url = "https://hackathon-i-ai-book-rag-chatbotfina.vercel.app/api/query"

    payload = {
        "question": "What are the key characteristics and design principles of Humanoid Robotics, according to the textbook?",
        "top_k": 3
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Please make sure the FastAPI server is running on https://hackathon-i-ai-book-rag-chatbotfina.vercel.app")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    test_query_endpoint()