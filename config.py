"""Configuration — all env vars and constants live here."""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Telegram
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8387873012"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Limits
MAX_ACCOUNTS = 500   # total across all users
MAX_PER_USER = 50

# Storage
DATA_FILE = os.environ.get("DATA_FILE", "users_data.json")

# AI (Groq)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
AI_MODEL = "llama-3.1-8b-instant"

# Email
IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
POLL_INTERVAL = 3        # seconds between IMAP checks
MAX_BODY_LENGTH = 2000   # chars to extract from email body
MAX_ERRORS = 10          # consecutive errors before stopping monitor
REPLY_CACHE_SIZE = 200   # max cached emails for reply
