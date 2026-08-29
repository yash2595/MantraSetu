"""Verification script for /health endpoint under DB-down failure scenario & recovery"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient
from app.core.app import create_app
from app.database.connection import close_db_client, init_db_client, _mongo_client

def test_db_down_failure_scenario():
    print("\n=======================================================")
    print("=== STARTING /health DB-DOWN FAILURE SCENARIO TEST ===")
    print("=======================================================")
    
    # ── STEP 1: VERIFY HEALTHY INITIAL STATE ──
    app = create_app()
    with TestClient(app) as client:
        print("\n--- 1. NORMAL HEALTHY STATE PROBE ---")
        res_healthy = client.get("/health")
        payload_healthy = res_healthy.json()
        print(f"HTTP Status: {res_healthy.status_code}")
        print("Payload:", payload_healthy)
        assert res_healthy.status_code == 200, f"Expected 200, got {res_healthy.status_code}"
        assert payload_healthy["healthy"] is True, "Expected healthy == True"
        assert payload_healthy["components"]["mongodb"]["status"] == "healthy"

        # ── STEP 2: SIMULATE DB DOWN (WRONG UNREACHABLE PORT 27019) ──
        print("\n--- 2. SIMULATING DB DOWN (UNREACHABLE PORT 27019) ---")
        close_db_client()
        os.environ["MONGODB_URI"] = "mongodb://127.0.0.1:27019/invalid_port"
        init_db_client()
        
        res_down = client.get("/health")
        payload_down = res_down.json()
        print(f"HTTP Status: {res_down.status_code}")
        print("Payload:", payload_down)
        
        assert res_down.status_code == 503, f"Expected 503, got {res_down.status_code}"
        assert payload_down["healthy"] is False, "Expected healthy == False"
        assert payload_down["status"] == "unhealthy", "Expected overall status == 'unhealthy'"
        assert payload_down["components"]["mongodb"]["status"] == "unhealthy", "Expected mongodb status == 'unhealthy'"
        print("SUCCESS: DB-down correctly triggered 503 Service Unavailable & unhealthy status without server crash!")

        # ── STEP 3: RECOVERY PASS (RESTORE VALID MONGO URI) ──
        print("\n--- 3. RECOVERY PASS (RESTORING MONGO CONNECTION) ---")
        close_db_client()
        os.environ["MONGODB_URI"] = "mongodb://127.0.0.1:27017/mantrasetu"
        init_db_client()
        
        res_recovery = client.get("/health")
        payload_recovery = res_recovery.json()
        print(f"HTTP Status: {res_recovery.status_code}")
        print("Payload:", payload_recovery)
        
        assert res_recovery.status_code == 200, f"Expected 200, got {res_recovery.status_code}"
        assert payload_recovery["healthy"] is True, "Expected healthy == True after recovery"
        assert payload_recovery["components"]["mongodb"]["status"] == "healthy"
        print("SUCCESS: Recovery pass confirmed! /health recovered to 200 OK healthy status!")

if __name__ == "__main__":
    test_db_down_failure_scenario()
