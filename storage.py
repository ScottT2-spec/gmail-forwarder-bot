"""User data storage — load, save, query."""

import json, os
from config import DATA_FILE


def save_users(data):
    """Write user data to disk."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[storage] save error: {e}", flush=True)


def load_users():
    """Read user data from disk."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[storage] load error: {e}", flush=True)
    return {}


def get_user_channel(uid):
    """Get user's forwarding channel ID. Returns None for DM mode."""
    users = load_users()
    u = users.get(str(uid), {})
    ch = u.get("forward_channel")
    if ch:
        try:
            return int(ch)
        except:
            pass
    return None


def create_user(uid, name):
    """Create a new user entry if it doesn't exist."""
    from datetime import datetime
    users = load_users()
    if str(uid) not in users:
        users[str(uid)] = {
            "name": name,
            "register_date": datetime.now().isoformat(),
            "is_banned": False,
            "accounts": []
        }
        save_users(users)
    return users


def increment_email_count(uid, addr):
    """Bump the total_emails counter for an account."""
    from datetime import datetime
    users = load_users()
    if str(uid) in users:
        for a in users[str(uid)].get("accounts", []):
            if a["email"] == addr:
                a["total_emails"] = a.get("total_emails", 0) + 1
                a["last_email_time"] = datetime.now().isoformat()
                break
        save_users(users)
