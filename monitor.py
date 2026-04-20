"""IMAP email monitoring — watches Gmail inboxes in background threads."""

import imaplib, threading, time
from config import IMAP_HOST, POLL_INTERVAL, MAX_ERRORS, REPLY_CACHE_SIZE
from mailer import parse_email, format_html, strip_html_tags
from storage import get_user_channel, increment_email_count
from ai import summarize
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# Reply cache: {cache_key: {reply_to, subject, account_email, account_pwd, uid, timestamp}}
email_cache = {}


class Monitor:
    def __init__(self, bot):
        self.bot = bot
        self.active = {}

    def start(self, uid, addr, pwd):
        key = f"{uid}_{addr}"
        if key in self.active:
            return
        self.active[key] = True
        threading.Thread(target=self._loop, args=(uid, addr, pwd, key), daemon=True).start()

    def stop(self, uid, addr):
        self.active.pop(f"{uid}_{addr}", None)

    def stop_all(self, uid):
        for k in list(self.active):
            if k.startswith(f"{uid}_"):
                self.active.pop(k, None)

    def _loop(self, uid, addr, pwd, key):
        seen = set()
        errors = 0

        while self.active.get(key):
            try:
                conn = imaplib.IMAP4_SSL(IMAP_HOST, timeout=30)
                conn.login(addr, pwd)
                conn.select("inbox")

                status, data = conn.search(None, 'UNSEEN')
                if status == "OK" and data[0]:
                    for eid in data[0].split():
                        if eid in seen:
                            continue
                        self._process_email(conn, eid, uid, addr, pwd)
                        seen.add(eid)
                        if len(seen) > 50:
                            seen = set(list(seen)[-25:])

                try:
                    conn.logout()
                except:
                    pass
                errors = 0

            except Exception:
                errors += 1
                if errors >= MAX_ERRORS:
                    try:
                        self.bot.send_message(uid, f"⚠️ Stopped monitoring {addr} - connection errors")
                    except:
                        pass
                    break
                time.sleep(min(3 * (2 ** errors), 60))
                continue

            time.sleep(POLL_INTERVAL)

        self.active.pop(key, None)

    def _process_email(self, conn, eid, uid, addr, pwd):
        """Fetch, parse, summarize, and forward a single email."""
        s2, md = conn.fetch(eid, "(RFC822)")
        if s2 != "OK" or not md or not md[0] or not isinstance(md[0], tuple):
            return

        email_data = parse_email(md[0][1])
        subj = email_data["subject"]
        sender = email_data["sender"]
        body = email_data["body"]
        reply_email = email_data["reply_email"]

        # AI summary
        summary = summarize(subj, sender, body)

        # Format message
        txt = format_html(subj, sender, body, summary)

        # Buttons
        cache_key = f"{uid}_{int(time.time() * 1000)}"
        reply_mk = InlineKeyboardMarkup()
        if summary:
            reply_mk.add(InlineKeyboardButton("📖 Read Full", callback_data=f"full_{cache_key}"))
        reply_mk.add(InlineKeyboardButton("↩️ Reply", callback_data=f"reply_{cache_key}"))

        # Send
        target_chat = get_user_channel(uid) or uid
        try:
            try:
                self.bot.send_message(target_chat, txt, parse_mode="HTML", reply_markup=reply_mk)
            except:
                self.bot.send_message(target_chat, strip_html_tags(txt), reply_markup=reply_mk)

            # Cache for reply + read full
            email_cache[cache_key] = {
                "reply_to": reply_email,
                "subject": subj,
                "sender": sender,
                "body": body,
                "summary": summary,
                "account_email": addr,
                "account_pwd": pwd,
                "uid": uid,
                "timestamp": time.time()
            }
            _trim_cache()

            increment_email_count(uid, addr)

        except Exception as e:
            print(f"[monitor] send error {uid}: {e}", flush=True)
            try:
                self.bot.send_message(uid, txt)
            except:
                pass


def _trim_cache():
    """Keep reply cache from growing too large."""
    if len(email_cache) > REPLY_CACHE_SIZE:
        oldest = sorted(email_cache, key=lambda k: email_cache[k]["timestamp"])[:REPLY_CACHE_SIZE // 2]
        for k in oldest:
            email_cache.pop(k, None)
