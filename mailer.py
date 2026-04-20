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

    # Body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                pl = part.get_payload(decode=True)
                if pl:
                    body = pl.decode(errors='ignore')[:MAX_BODY_LENGTH]
                    break
    else:
        pl = msg.get_payload(decode=True)
        if pl:
            body = pl.decode(errors='ignore')[:MAX_BODY_LENGTH]

    # Clean body
    body = _clean_body(body)

    return {
        "subject": subj,
        "sender": sender,
        "reply_email": reply_email,
        "body": body
    }


def _clean_body(body):
    """Remove newsletter noise from email body."""
    body = re.sub(r'<[^>]+>', '', body)                   # strip HTML
    body = re.sub(r'View image: \([^)]+\)', '', body)     # remove image refs
    body = re.sub(r'Caption:\s*', '', body)               # empty captions
    body = re.sub(r'https?://\S+', '', body)              # bare URLs
    body = re.sub(r'-{3,}', '', body)                     # separators
    body = re.sub(r'\n{3,}', '\n\n', body)                # excess newlines
    return body.strip() or "No text content"


def format_html(subject, sender, body, summary=None):
    """Format an email into an HTML Telegram message."""
    safe_subj = htmlmod.escape(subject)
    safe_sender = htmlmod.escape(sender)

    # Convert *bold* and _italic_ in body
    body_html = htmlmod.escape(body)
    body_html = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', body_html)
    body_html = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<i>\1</i>', body_html)

    summary_line = ""
    if summary:
        summary_line = f"\n🤖 <b>{htmlmod.escape(summary)}</b>\n"

    from datetime import datetime
    return (
        f"📧 New Email{summary_line}\n"
        f"📍 Subject: {safe_subj}\n"
        f"👤 From: {safe_sender}\n\n"
        f"📝 Content:\n{body_html}\n\n"
        f"⚡ Received at {datetime.now().strftime('%H:%M:%S')}"
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
