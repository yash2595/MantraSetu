import requests
import uuid

BASE_URL = "http://localhost:8000"

def test_duplicate_signup():
    email = "test_duplicate@mantrasetu.com"
    user_data = {
        "name": "Test User",
        "email": email,
        "phone": "1234567890",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }
    # First signup
    res1 = requests.post(f"{BASE_URL}/auth/signup", json=user_data)
    print("Signup 1:", res1.status_code)
    
    # Second signup with same email
    res2 = requests.post(f"{BASE_URL}/auth/signup", json=user_data)
    print("Signup 2 (Duplicate):", res2.status_code, res2.text)
    
    return res1.json().get("access_token")

def test_invalid_booking(token):
    res = requests.post(f"{BASE_URL}/puja/book", json={
        "puja_id": "this_puja_does_not_exist_at_all",
        "city": "Varanasi",
        "date": "2026-01-01",
        "time": "10:00 AM",
        "devotee_name": "Devotee",
        "phone": "1234567890"
    }, headers={"Authorization": f"Bearer {token}"})
    print("Invalid Booking:", res.status_code, res.text)

if __name__ == "__main__":
    token = test_duplicate_signup()
    if token:
        test_invalid_booking(token)
