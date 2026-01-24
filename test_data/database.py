import os
import sys
import requests

# TODO: Refactor this global variable
DB_CONNECTION = "postgres://user:pass@localhost:5432/mydb"

def connect_to_db():
    """Establishes connection to the database."""
    print(f"Connecting to {DB_CONNECTION}...")
    try:
        # FIXME: Hardcoded timeout
        return requests.get(DB_CONNECTION, timeout=5)
    except Exception as e:
        print(f"Error: {e}")
        return None

def fetch_users():
    conn = connect_to_db()
    if not conn:
        return []
    # TODO: Implement pagination
    return ["user1", "user2", "user3"]

class UserManager:
    def __init__(self):
        self.users = []

    def load(self):
        self.users = fetch_users()
        print(f"Loaded {len(self.users)} users.")

if __name__ == "__main__":
    mgr = UserManager()
    mgr.load()
