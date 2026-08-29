import io
import sys
from fastapi.testclient import TestClient
from app.main import app
import contextlib

client = TestClient(app)

def run_test(name, method, url, data=None, files=None, headers=None, expect_status=None):
    print(f"\n=========================================")
    print(f"TEST: {name}")
    print(f"REQUEST: {method} {url}")
    if data: print(f"DATA: {data}")
    
    # Capture stdout
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        if method == "POST":
            response = client.post(url, json=data if not files else None, data=data if files else None, files=files, headers=headers)
        elif method == "GET":
            response = client.get(url, headers=headers)
    
    output = f.getvalue()
    print(f"\n[TERMINAL OUTPUT (PRINT STATEMENTS)]\n{output.strip() if output.strip() else '<No output>'}")
    
    print(f"\n[RESPONSE]")
    print(f"STATUS CODE: {response.status_code}")
    print(f"BODY: {response.json() if response.text else ''}")
    
    if expect_status and response.status_code != expect_status:
        print(f"\n[FAILED] Expected {expect_status}, got {response.status_code}")
    else:
        print(f"\n[PASSED]")
    
    return output, response

import uuid
email_prefix = str(uuid.uuid4())[:8]
devotee_email = f"testdevotee_{email_prefix}@example.com"
pandit_email = f"panditji_{email_prefix}@example.com"

# 1. Devotee Signup - Happy Path
out, res = run_test(
    "Devotee Signup - Happy Path", "POST", "/auth/signup",
    data={"name": "Test Devotee", "email": devotee_email, "phone": "1234567890", "password": "password123", "confirm_password": "password123"},
    expect_status=201
)

# 2. Devotee Signup - Invalid Fields (mismatched password)
run_test(
    "Devotee Signup - Mismatched Password", "POST", "/auth/signup",
    data={"name": "Test Devotee", "email": devotee_email, "phone": "1234567890", "password": "password123", "confirm_password": "password456"},
    expect_status=422
)

# 3. Devotee Login - Happy Path
run_test(
    "Devotee Login - Happy Path", "POST", "/auth/login",
    data={"email": devotee_email, "password": "password123"},
    expect_status=200
)

# 4. Devotee Login - Wrong Password
run_test(
    "Devotee Login - Unauthorized", "POST", "/auth/login",
    data={"email": devotee_email, "password": "wrongpassword"},
    expect_status=401
)

# 5. Pandit Apply - Happy Path (Using Form Data as it requires multipart/form-data)
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

run_test(
    "Pandit Apply - Happy Path", "POST", "/pandit/apply",
    data=pandit_data,
    expect_status=201
)

print("\n\nAll targeted endpoint tests executed.")
