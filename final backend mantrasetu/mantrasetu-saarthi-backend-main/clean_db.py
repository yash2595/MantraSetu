import pymongo

def clean_db():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["mantrasetu"]
    
    # Clean users duplicate emails
    users = list(db.users.find())
    seen_emails = set()
    for user in users:
        email = user.get("email")
        if email in seen_emails:
            print(f"Deleting duplicate user: {email}")
            db.users.delete_one({"_id": user["_id"]})
        else:
            seen_emails.add(email)

    # Clean pandit_applications duplicate emails
    pandits = list(db.pandit_applications.find())
    seen_emails = set()
    for pandit in pandits:
        email = pandit.get("email")
        if email in seen_emails:
            print(f"Deleting duplicate pandit: {email}")
            db.pandit_applications.delete_one({"_id": pandit["_id"]})
        else:
            seen_emails.add(email)

    # Clean orphaned bookings
    db.puja_bookings.delete_many({"puja_id": "dummy_puja"})
    print("Deleted orphaned bookings.")
    
    client.close()

if __name__ == "__main__":
    clean_db()
