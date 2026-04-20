"""AI email summaries via Groq."""

import json, urllib.request
from config import GROQ_API_KEY, AI_MODEL


def summarize(subject, sender, body):
    """Generate a one-line AI summary of an email. Returns None on failure."""
    if not GROQ_API_KEY:
        return None
    try:
        prompt = (
            "Summarize this email in 2-3 sentences. Cover the key points so someone "
            "doesn't need to read the full email. Just the summary, nothing else.\n\n"
            f"From: {sender}\nSubject: {subject}\nBody: {body[:800]}"
        )
        payload = json.dumps({
            "model": AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.3
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "GmailForwarderBot/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ai] summary error: {e}", flush=True)
        return None
