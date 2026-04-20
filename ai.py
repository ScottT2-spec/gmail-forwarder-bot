"""AI email summaries via Groq."""

import json, urllib.request
from config import GROQ_API_KEY, AI_MODEL


def summarize(subject, sender, body):
    """Generate a one-line AI summary of an email. Returns None on failure."""
    if not GROQ_API_KEY:
        return None
    try:
        prompt = (
            "Summarize this email in one short sentence (max 15 words). "
            "Just the summary, nothing else.\n\n"
            f"From: {sender}\nSubject: {subject}\nBody: {body[:500]}"
        )
        payload = json.dumps({
            "model": AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.3
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ai] summary error: {e}", flush=True)
        return None
