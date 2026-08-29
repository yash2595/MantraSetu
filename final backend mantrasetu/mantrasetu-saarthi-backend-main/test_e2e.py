import requests
import time
import json
import uuid
import os

BASE_URL = "http://localhost:8000"
test_user = {
    "name": "Test E2E User",
    "email": f"teste2e_{uuid.uuid4().hex[:6]}@mantrasetu.com",
    "phone": "9876543210",
    "password": "TestPassword123!",
    "confirm_password": "TestPassword123!"
}

results = []

def run_test(name, func):
    try:
        res = func()
        if res:
            results.append(f"PASS: {name}")
            print(f"PASS: {name}")
        else:
            results.append(f"FAIL: {name} (Returned False)")
            print(f"FAIL: {name}")
    except Exception as e:
        results.append(f"FAIL: {name} - Exception: {str(e)}")
        print(f"FAIL: {name} - Exception: {str(e)}")

token = None
user_id = None

def test_signup():
    global token, user_id
    r = requests.post(f"{BASE_URL}/auth/signup", json=test_user)
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        return True
    elif r.status_code == 409:
        # Already exists, try login
        return True
    print("Signup failed:", r.text)
    return False

def test_login():
    global token, user_id
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        return True
    print("Login failed:", r.text)
    return False

def test_puja_list():
    r = requests.get(f"{BASE_URL}/puja/list")
    if r.status_code == 200:
        return True
    print("Puja List failed:", r.text)
    return False

def test_puja_book():
    # Attempt to book a puja
    r = requests.post(f"{BASE_URL}/puja/book", json={
        "puja_id": "dummy_puja",
        "city": "TestCity",
        "date": "2026-10-10",
        "time": "10:00 AM",
        "devotee_name": "Test Devotee",
        "phone": "9876543210"
    }, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return True
    print("Puja book failed:", r.text)
    return False

def test_pandit_apply():
    with open("dummy_aadhaar.pdf", "wb") as f:
        f.write(b"dummy content")
    with open("dummy_cert.pdf", "wb") as f:
        f.write(b"dummy content")
        
    url = f"{BASE_URL}/pandit/apply"
    data = {
        "name": "Pandit E2E",
        "email": f"pandit_{uuid.uuid4().hex[:6]}@mantrasetu.com",
        "phone": "9998887776",
        "password": "PanditPassword1!",
        "confirm_password": "PanditPassword1!",
        "city": "Varanasi",
        "state": "UP",
        "experience": "10 years",
        "specialization": "Vedic, Vivah",
        "languages": "Hindi",
    }
    files = {
        "aadhaar_file": ("dummy_aadhaar.pdf", open("dummy_aadhaar.pdf", "rb"), "application/pdf"),
        "certificate_file": ("dummy_cert.pdf", open("dummy_cert.pdf", "rb"), "application/pdf")
    }
    r = requests.post(url, data=data, files=files)
    if r.status_code == 200:
        return True
    print("Pandit Apply failed:", r.text)
    return False

def test_kundali():
    r = requests.post(f"{BASE_URL}/kundali/generate", json={
        "name": "Test Kundali",
        "dob": "1990-01-01",
        "tob": "12:00",
        "pob": "Delhi",
        "gender": "Male"
    }, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return True
    print("Kundali failed:", r.text)
    return False

def test_contact():
    r = requests.post(f"{BASE_URL}/contact", json={
        "name": "Contact User",
        "email": "contact@mantrasetu.com",
        "topic": "General Inquiry",
        "message": "Testing the contact form"
    })
    if r.status_code == 200:
        return True
    print("Contact failed:", r.text)
    return False

def test_voice_ticket():
    r = requests.post(f"{BASE_URL}/voice/ticket", headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        data = r.json()
        if "ticket" in data:
            return True
    print("Voice Ticket failed:", r.text)
    return False


print("Running E2E tests...")
run_test("User Signup", test_signup)
run_test("User Login", test_login)
run_test("Puja Catalog Browse", test_puja_list)
run_test("Puja Booking", test_puja_book)
run_test("Pandit Application", test_pandit_apply)
run_test("Kundali Generation", test_kundali)
run_test("Contact Form", test_contact)
run_test("Voice Ticket Generation", test_voice_ticket)

print("\\n--- SUMMARY ---")
for res in results:
    print(res)
