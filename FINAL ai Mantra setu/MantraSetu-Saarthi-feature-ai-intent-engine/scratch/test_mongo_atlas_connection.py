"""Test MongoDB Atlas connection & read/write sanity check."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

import pymongo

def test_atlas():
    mongo_uri = os.getenv("MONGODB_URI")
    print(f"Loaded MONGODB_URI: {mongo_uri[:35]}... (Redacted sensitive parts)")
    
    if "<username>" in mongo_uri or "<password>" in mongo_uri:
        print("RESULT: MONGODB_URI still contains '<username>' or '<password>' placeholders.")
        print("ACTION NEEDED: Update .env with your rotated Atlas username/password.")
        return False
        
    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Ping server to confirm connection
        res = client.admin.command('ping')
        print(f"MongoDB Ping Successful: {res}")
        
        db_name = os.getenv("DATABASE_NAME") or mongo_uri.split("?")[0].rstrip("/").split("/")[-1] or "mantrasetu"
        db = client[db_name]
        print(f"Connected to Database: '{db.name}' on Atlas Cluster")
        
        # Test read/write sanity check on 'connection_test' collection
        col = db["connection_test"]
        test_doc = {"test": "atlas_connection_check", "status": "active"}
        insert_res = col.insert_one(test_doc)
        print(f"Sanity Write OK: inserted_id={insert_res.inserted_id}")
        
        found = col.find_one({"_id": insert_res.inserted_id})
        print(f"Sanity Read OK: found={found['_id']}")
        
        col.delete_one({"_id": insert_res.inserted_id})
        print("Sanity Delete OK. MongoDB Atlas Connection FULLY VERIFIED.")
        client.close()
        return True
    except Exception as e:
        print(f"MongoDB Atlas Connection FAILED: {e}")
        return False

if __name__ == "__main__":
    test_atlas()
