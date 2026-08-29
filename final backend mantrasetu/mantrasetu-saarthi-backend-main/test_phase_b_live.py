import requests
import uuid

BASE_URL = "http://127.0.0.1:8000"

email_prefix = str(uuid.uuid4())[:8]
devotee_email = f"testdevotee_{email_prefix}@example.com"
pandit_email = f"panditji_{email_prefix}@example.com"

def run_test(name, method, endpoint, data=None):
    print(f"\n=========================================")
    print(f"TEST: {name}")
    print(f"REQUEST: {method} {endpoint}")
    url = BASE_URL + endpoint
    
    if method == "POST":
        response = requests.post(url, json=data)
    
    print(f"[RESPONSE]")
    print(f"STATUS CODE: {response.status_code}")
    print(f"BODY: {response.text}")
    
# 1. Devotee Signup - Happy Path
run_test(
    "Devotee Signup - Happy Path", "POST", "/auth/signup",
    data={"name": "Test Devotee", "email": devotee_email, "phone": "1234567890", "password": "password123", "confirm_password": "password123"}
)

# 2. Devotee Signup - Invalid Fields (mismatched password)
run_test(
    "Devotee Signup - Mismatched Password", "POST", "/auth/signup",
    data={"name": "Test Devotee", "email": devotee_email, "phone": "1234567890", "password": "password123", "confirm_password": "password456"}
)

# 3. Devotee Login - Happy Path
run_test(
    "Devotee Login - Happy Path", "POST", "/auth/login",
    data={"email": devotee_email, "password": "password123"}
)

# 4. Devotee Login - Wrong Password
run_test(
    "Devotee Login - Unauthorized", "POST", "/auth/login",
    data={"email": devotee_email, "password": "wrongpassword"}
)

# 5. Pandit Apply - Happy Path (Using Form Data)
pandit_data = {
    "name": "Pandit Ji",
    "email": pandit_email,
    "phone": "0987654321",
    "password": "password123",
    "confirm_password": "password123",
    "city": "Varanasi",
    "state": "UP",
    "experience": "10 years",
    "languages": "Hindi",
    "specialization": "Puja"
}
print(f"\n=========================================")
print(f"TEST: Pandit Apply - Happy Path")
print(f"REQUEST: POST /pandit/apply")
response = requests.post(BASE_URL + "/pandit/apply", data=pandit_data)
print(f"[RESPONSE]")
print(f"STATUS CODE: {response.status_code}")
print(f"BODY: {response.text}")

print("\n\nAll targeted endpoint tests executed.")
