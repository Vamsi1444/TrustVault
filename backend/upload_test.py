import requests

BASE_URL = "http://127.0.0.1:5000"

login = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "email": "alice@test.com",
        "password": "TrustVault@2026Secure"
    }
)

login.raise_for_status()
token = login.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

with open("test-document.txt", "rb") as file:
    response = requests.post(
        f"{BASE_URL}/api/documents/upload",
        headers=headers,
        files={"file": ("test-document.txt", file, "text/plain")},
        data={
            "title": "Corrected Test Document",
            "category": "Testing"
        }
    )

print("Status:", response.status_code)
print("Response:", response.text)