import requests

res = requests.post("http://localhost:8000/voice/ticket")
print(f"Status Code: {res.status_code}")
print("Response JSON:", res.json())
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert "ticket" in res.json(), "Expected ticket in response"
print("SUCCESS: /voice/ticket endpoint returned valid WebSocket ticket!")
