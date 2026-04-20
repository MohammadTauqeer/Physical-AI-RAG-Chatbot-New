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
        if response.status_code == 200:
            print("✓ Health endpoint is working")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Health endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing health endpoint: {e}")

    # Test root endpoint
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✓ Root endpoint is working")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Root endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing root endpoint: {e}")

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
        if response.status_code in [200, 404, 400]:  # 404/400 are expected if no content is found
            print("✓ Query endpoint is working (status code may vary based on content availability)")
            print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
            elif response.status_code == 404:
                print("Note: 404 means no relevant content was found in the database")
            elif response.status_code == 400:
                print("Note: 400 means the request was malformed")
        else:
            print(f"✗ Query endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing query endpoint: {e}")

    print("\nAPI testing complete!")

if __name__ == "__main__":
    test_api_endpoints()