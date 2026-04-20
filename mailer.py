"""Email operations — SMTP reply and body parsing."""

import re, smtplib, html as htmlmod
import email as emaillib
from email.header import decode_header
from email.mime.text import MIMEText
from config import SMTP_HOST, SMTP_PORT, MAX_BODY_LENGTH


def parse_email(raw_bytes):
    """Parse raw email bytes into a clean dict."""
    msg = emaillib.message_from_bytes(raw_bytes)

    # Subject
    raw_subj = decode_header(msg.get("subject", ""))[0]
    subj = raw_subj[0] or ""
    if isinstance(subj, bytes):
        subj = subj.decode(raw_subj[1] or 'utf-8', errors='ignore')
    subj = str(subj)

    # Sender
    sender = msg.get("from", "")

    # Reply-to address
    reply_to = msg.get("reply-to", sender)
    email_match = re.search(r'[\w.-]+@[\w.-]+', reply_to)
    reply_email = email_match.group() if email_match else ""

    # Body — prefer text/plain, fall back to text/html
    body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not body:
                pl = part.get_payload(decode=True)
                if pl:
                    body = pl.decode(errors='ignore')[:MAX_BODY_LENGTH]
            elif ct == "text/html" and not html_body:
                pl = part.get_payload(decode=True)
                if pl:
                    html_body = pl.decode(errors='ignore')[:MAX_BODY_LENGTH * 2]
    else:
        ct = msg.get_content_type()
        pl = msg.get_payload(decode=True)
        if pl:
            if ct == "text/plain":
                body = pl.decode(errors='ignore')[:MAX_BODY_LENGTH]
            elif ct == "text/html":
                html_body = pl.decode(errors='ignore')[:MAX_BODY_LENGTH * 2]

    # If no plain text, extract from HTML
    if not body.strip() and html_body:
        body = _html_to_text(html_body)[:MAX_BODY_LENGTH]

    # Clean body
    body = _clean_body(body)

    return {
        "subject": subj,
        "sender": sender,
        "reply_email": reply_email,
        "body": body
    }


def _html_to_text(html_str):
    """Convert HTML email to readable plain text."""
    # Remove style and script blocks entirely
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br> and block elements with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = htmlmod.unescape(text)
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)           # collapse spaces
    text = re.sub(r'\n[ \t]+', '\n', text)         # strip leading spaces on lines
    text = re.sub(r'\n{3,}', '\n\n', text)         # collapse blank lines
    return text.strip()


def _clean_body(body):
    """Remove newsletter noise from email body."""
    body = re.sub(r'<[^>]+>', '', body)                   # strip HTML
    body = re.sub(r'View image: \([^)]+\)', '', body)     # remove image refs
    body = re.sub(r'Caption:\s*', '', body)               # empty captions
    body = re.sub(r'https?://\S+', '', body)              # bare URLs
    body = re.sub(r'-{3,}', '', body)                     # separators
    body = re.sub(r'\n{3,}', '\n\n', body)                # excess newlines
    return body.strip() or "No text content"


def format_summary_view(subject, sender, summary):
    """Format the compact summary view (default)."""
    safe_subj = htmlmod.escape(subject)
    safe_sender = htmlmod.escape(sender)
    safe_summary = htmlmod.escape(summary)

    from datetime import datetime
    return (
        f"📧 New Email\n\n"
        f"📍 Subject: {safe_subj}\n"
        f"👤 From: {safe_sender}\n\n"
        f"🤖 <b>Summary:</b>\n{safe_summary}\n\n"
        f"⚡ {datetime.now().strftime('%H:%M:%S')}"
    )


def format_full_view(subject, sender, body, summary):
    """Format the full email view (after tapping Read Full)."""
    safe_subj = htmlmod.escape(subject)
    safe_sender = htmlmod.escape(sender)
    safe_summary = htmlmod.escape(summary) if summary else ""

    body_html = htmlmod.escape(body)
    body_html = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', body_html)
    body_html = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<i>\1</i>', body_html)

    summary_block = f"🤖 <b>Summary:</b>\n{safe_summary}\n\n" if safe_summary else ""

    from datetime import datetime
    return (
        f"📧 Full Email\n\n"
        f"📍 Subject: {safe_subj}\n"
        f"👤 From: {safe_sender}\n\n"
        f"{summary_block}"
        f"📝 <b>Content:</b>\n{body_html}\n\n"
        f"⚡ {datetime.now().strftime('%H:%M:%S')}"
    )


def format_html(subject, sender, body, summary=None):
    """Format email — summary view if AI available, full view otherwise."""
    if summary:
        return format_summary_view(subject, sender, summary)
    # No AI summary — show full email
    safe_subj = htmlmod.escape(subject)
    safe_sender = htmlmod.escape(sender)

    body_html = htmlmod.escape(body)
    body_html = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', body_html)
    body_html = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<i>\1</i>', body_html)

    from datetime import datetime
    return (
        f"📧 New Email\n\n"
        f"📍 Subject: {safe_subj}\n"
        f"👤 From: {safe_sender}\n\n"
        f"📝 Content:\n{body_html}\n\n"
        f"⚡ {datetime.now().strftime('%H:%M:%S')}"
    )


def strip_html_tags(text):
    """Remove HTML tags for plain-text fallback."""
    return text.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')


def send_reply(account_email, account_pwd, to_addr, subject, body_text):
    """Send a reply via SMTP. Returns (success, error_msg)."""
    try:
        msg = MIMEText(body_text)
        msg["Subject"] = f"Re: {subject}"
        msg["From"] = account_email
        msg["To"] = to_addr
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(account_email, account_pwd)
            smtp.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)
