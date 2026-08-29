import asyncio
import pymongo
from pymongo import MongoClient

def check_db_integrity():
    print("Connecting to MongoDB...")
    client = MongoClient("mongodb://localhost:27017/")
    db = client["mantrasetu"]
    
    print("\\n--- COLLECTIONS ---")
    collections = db.list_collection_names()
    print(collections)
    
    print("\\n--- INDEXES ---")
    for coll_name in collections:
        print(f"\\nIndexes for {coll_name}:")
        indexes = db[coll_name].index_information()
        for name, info in indexes.items():
            print(f"  - {name}: {info}")
            
    print("\\n--- SCHEMA CHECK (Sampling 1 doc from each) ---")
    for coll_name in collections:
        doc = db[coll_name].find_one()
        if doc:
            print(f"\\nCollection {coll_name} Sample keys:")
            print(list(doc.keys()))
        else:
            print(f"\\nCollection {coll_name} is empty.")
            
    print("\\n--- ORPHAN CHECK ---")
    # Check bookings for orphaned users
    bookings = list(db["bookings"].find())
    orphaned_bookings = []
    for b in bookings:
        user_id = b.get("user_id")
        if user_id:
            # Need to convert user_id back to ObjectId to check? The backend saves them as strings or ObjectIds?
            # Let's check how they are stored.
            user = db["users"].find_one({"_id": user_id})
            if not user:
                from bson.objectid import ObjectId
                try:
                    user = db["users"].find_one({"_id": ObjectId(user_id)})
                except:
                    pass
            
            if not user:
                orphaned_bookings.append(b.get("_id"))
                
    if orphaned_bookings:
        print(f"Found {len(orphaned_bookings)} orphaned bookings: {orphaned_bookings}")
    else:
        print("No orphaned bookings found for user_id.")
        
    client.close()

if __name__ == "__main__":
    check_db_integrity()
