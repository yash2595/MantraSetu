import requests
import asyncio
import websockets
import json

def check_cors(url_base):
    print(f"\n--- Checking CORS for {url_base} ---")
    
    # 1. Allowed Origin
    req = requests.options(f"{url_base}/", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    })
    print(f"Allowed Origin (localhost:5173) -> Status: {req.status_code}")
    print(f"Access-Control-Allow-Origin header: {req.headers.get('Access-Control-Allow-Origin', 'MISSING')}")
    
    # 2. Malicious Origin
    req_mal = requests.options(f"{url_base}/", headers={
        "Origin": "http://malicious.com",
        "Access-Control-Request-Method": "GET"
    })
    print(f"Malicious Origin (malicious.com) -> Status: {req_mal.status_code}")
    print(f"Access-Control-Allow-Origin header: {req_mal.headers.get('Access-Control-Allow-Origin', 'MISSING')}")


async def test_ws_security():
    print(f"\n--- Checking WebSocket Security (AI Service: 8002) ---")
    
    # 1. No Origin, No Ticket
    print("\n[Test 1] No Origin, No Ticket")
    try:
        async with websockets.connect("ws://127.0.0.1:8002/ws/voice") as ws:
            print("[FAILED] Connection accepted when it should have been rejected.")
    except websockets.exceptions.InvalidStatus as e:
        print(f"[PASSED] Rejected with HTTP {e.response.status_code}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[PASSED] Closed with code {e.code}, reason: {e.reason}")

    # 2. Valid Origin, No Ticket
    print("\n[Test 2] Valid Origin, No Ticket")
    try:
        async with websockets.connect(
            "ws://127.0.0.1:8002/ws/voice", 
            additional_headers={"Origin": "http://localhost:5173"}
        ) as ws:
            print("[FAILED] Connection accepted when it should have been rejected.")
    except websockets.exceptions.InvalidStatus as e:
        print(f"[PASSED] Rejected with HTTP {e.response.status_code}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[PASSED] Closed with code {e.code}, reason: {e.reason}")

    # 3. Valid Origin, Invalid Ticket
    print("\n[Test 3] Valid Origin, Invalid Ticket")
    try:
        async with websockets.connect(
            "ws://127.0.0.1:8002/ws/voice?ticket=FAKE_TICKET_123", 
            additional_headers={"Origin": "http://localhost:5173"}
        ) as ws:
            print("[FAILED] Connection accepted when it should have been rejected.")
    except websockets.exceptions.InvalidStatus as e:
        print(f"[PASSED] Rejected with HTTP {e.response.status_code}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[PASSED] Closed with code {e.code}, reason: {e.reason}")


if __name__ == "__main__":
    check_cors("http://127.0.0.1:8000")
    check_cors("http://127.0.0.1:8002")
    
    asyncio.run(test_ws_security())
