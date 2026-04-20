import requests
import json

def test_api_endpoints():
    """
    Simple test script to verify the API endpoints are working
    """
    base_url = "https://hackathon-i-ai-book-rag-chatbotfina.vercel.app"

    # Test health endpoint
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health")
        print("Health endpoint response:", response.status_code, response.json())
    except Exception as e:
        print("Error testing health endpoint:", e)

    # Test root endpoint
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print("Root endpoint response:", response.status_code, response.json())
    except Exception as e:
        print("Error testing root endpoint:", e)

    # Test query endpoint (with a sample request)
    print("\nTesting query endpoint...")
    try:
        sample_request = {
            "question": "What is Physical AI?",
            "top_k": 2
        }
        response = requests.post(
            f"{base_url}/api/query",
            headers={"Content-Type": "application/json"},
            data=json.dumps(sample_request)
        )
        print("Query endpoint response:", response.status_code)
        if response.content:
            print("Response body:", response.json())
        else:
            print("Empty response body")
    except Exception as e:
        print("Error testing query endpoint:", e)

    print("\nAPI testing complete!")

if __name__ == "__main__":
    test_api_endpoints()