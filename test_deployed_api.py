import requests
import json

def test_deployed_api():
    url = "https://hackathon-i-ai-book-rag-chatbotfina.vercel.app/api/query"

    payload = {
        "query": "What is a humanoid robot?"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

        # Check if we got a successful response
        if response.status_code == 200:
            print("\n✅ SUCCESS: API is working correctly!")
            print(f"Answer: {response.json().get('answer', 'No answer field in response')}")
        else:
            print(f"\n❌ ERROR: Received status code {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Please make sure the deployed API is accessible.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    test_deployed_api()