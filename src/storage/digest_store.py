import json
import os
from datetime import datetime

DIGESTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "digests")

def save_digest(digest, date_str=None):
    """
    Saves today's digest JSON to digests/YYYY-MM-DD.json
    date_str: optional override, defaults to today
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(DIGESTS_DIR, exist_ok=True)
    path = os.path.join(DIGESTS_DIR, f"{date_str}.json")

    with open(path, "w") as f:
        json.dump(digest, f, indent=2)

    print(f"[DigestStore] Saved to {path}")
    return path

def load_digest(date_str=None):
    """Loads a digest by date. Defaults to today."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    path = os.path.join(DIGESTS_DIR, f"{date_str}.json")

    if not os.path.exists(path):
        return None

    with open(path) as f:
        return json.load(f)