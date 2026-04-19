import telebot, imaplib, email as emaillib, threading, time, json, os, re
from email.header import decode_header
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("Starting Gmail Bot V3...", flush=True)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8387873012"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
MAX_ACCOUNTS = 500  # total across all users
MAX_PER_USER = 50
DATA_FILE = os.environ.get("DATA_FILE", "users_data.json")

bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

def save_users(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def load_users():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {}

def get_user_channel(uid):
    """Get user's configured forwarding channel. Returns None if not set (DM mode)."""
    users = load_users()
    u = users.get(str(uid), {})
    ch = u.get("forward_channel")
    if ch:
        try: return int(ch)
        except: pass
    return None

def user_menu(uid):
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    users = load_users()
    if str(uid) in users and users[str(uid)].get("accounts"):
        m.add(KeyboardButton("Add Email"), KeyboardButton("My Stats"),
              KeyboardButton("My Accounts"), KeyboardButton("Delete Account"),
              KeyboardButton("Set Channel"), KeyboardButton("Refresh"))
        if uid == ADMIN_ID:
            m.add(KeyboardButton("Admin"))
    else:
        m.add(KeyboardButton("Add Email"), KeyboardButton("Set Channel"))
        if uid == ADMIN_ID:
            m.add(KeyboardButton("Admin"))
    return m

def admin_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(KeyboardButton("All Users"), KeyboardButton("All Accounts"),
          KeyboardButton("Broadcast"), KeyboardButton("System Stats"),
          KeyboardButton("Ban Manager"), KeyboardButton("Logout Admin"))
    return m

class Monitor:
    def __init__(self):
        self.active = {}
    
    def start(self, uid, addr, pwd):
        key = f"{uid}_{addr}"
        if key in self.active: return
        self.active[key] = True
        def loop():
            seen = set()
            errors = 0
            while self.active.get(key):
                try:
                    m = imaplib.IMAP4_SSL("imap.gmail.com", timeout=30)
                    m.login(addr, pwd)
                    m.select("inbox")
                    s, d = m.search(None, 'UNSEEN')
                    if s == "OK" and d[0]:
                        for eid in d[0].split():
                            if eid not in seen:
                                s2, md = m.fetch(eid, "(RFC822)")
                                if s2 == "OK" and md and md[0] and isinstance(md[0], tuple):
                                    msg = emaillib.message_from_bytes(md[0][1])
                                    subj = str(decode_header(msg.get("subject",""))[0][0] or "")
                                    if isinstance(subj, bytes): subj = subj.decode(errors='ignore')
                                    sender = msg.get("from","")
                                    body = ""
                                    if msg.is_multipart():
                                        for p in msg.walk():
                                            if p.get_content_type() == "text/plain":
                                                pl = p.get_payload(decode=True)
                                                if pl: body = pl.decode(errors='ignore')[:2000]; break
                                    else:
                                        pl = msg.get_payload(decode=True)
                                        if pl: body = pl.decode(errors='ignore')[:2000]
                                    body = re.sub(r'<[^>]+>','',body).strip() or "No text content"
                                    txt = f"📧 New Email\n\n📍 Subject: {subj}\n👤 From: {sender}\n\n📝 Content:\n{body}\n\n⚡ Received at {datetime.now().strftime('%H:%M:%S')}"
                                    try:
                                        # Forward to user's channel if set, otherwise DM
                                        target_chat = get_user_channel(uid) or uid
                                        bot.send_message(target_chat, txt)
                                        users = load_users()
                                        if str(uid) in users:
                                            for a in users[str(uid)].get("accounts",[]):
                                                if a["email"]==addr: a["total_emails"]=a.get("total_emails",0)+1; a["last_email_time"]=datetime.now().isoformat(); break
                                            save_users(users)
                                    except Exception as send_err:
                                        print(f"[send error] {uid} -> {send_err}", flush=True)
                                        # Fallback to DM if channel fails
                                        try: bot.send_message(uid, txt)
                                        except: pass
                                    seen.add(eid)
                                    if len(seen)>50: seen=set(list(seen)[-25:])
                    try: m.logout()
                    except: pass
                    errors = 0
                except:
                    errors += 1
                    if errors >= 10:
                        try: bot.send_message(uid, f"⚠️ Stopped monitoring {addr} - connection errors")
                        except: pass
                        break
                    time.sleep(min(3*(2**errors),60)); continue
                time.sleep(3)
            self.active.pop(key, None)
        threading.Thread(target=loop, daemon=True).start()
    
    def stop(self, uid, addr):
        self.active.pop(f"{uid}_{addr}", None)
    
    def stop_all(self, uid):
        for k in list(self.active):
            if k.startswith(f"{uid}_"): self.active.pop(k,None)

monitor = Monitor()

# ── Commands ──────────────────────────────────────────────────

@bot.message_handler(commands=['start','help'])
def cmd_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Friend"
    print(f"[start] {uid} {name}", flush=True)
    users = load_users()
    if str(uid) in users and users[str(uid)].get("accounts"):
        n = len(users[str(uid)]["accounts"])
        ch = users[str(uid)].get("forward_channel")
        ch_txt = f"\n📢 Channel: {ch}" if ch else "\n📢 Channel: DM (use 'Set Channel' to change)"
        bot.send_message(uid, f"Welcome back {name}!\n\n📧 Accounts: {n}\n🔔 System active{ch_txt}", reply_markup=user_menu(uid))
    else:
        bot.send_message(uid, f"Welcome {name}!\n\n📧 Gmail Forwarder V3\nUp to {MAX_PER_USER} accounts\n\n📢 Set your channel first, then add emails.\n\nTap 'Set Channel' to start", reply_markup=user_menu(uid))

@bot.message_handler(func=lambda m: m.text == "Set Channel")
def cmd_set_channel(message):
    uid = message.from_user.id
    user_sessions[uid] = {"step": "set_channel"}
    users = load_users()
    current = users.get(str(uid), {}).get("forward_channel", "Not set (DMs)")
    bot.send_message(uid, 
        f"📢 Current channel: {current}\n\n"
        "Send me the channel/group ID where you want emails forwarded.\n\n"
        "How to get it:\n"
        "1. Add this bot as admin to your channel/group\n"
        "2. Send a message in the channel\n"
        "3. Forward that message to @userinfobot to get the ID\n"
        "4. Send the ID here (starts with -100...)\n\n"
        "Or send 'dm' to receive emails in this chat.")

@bot.message_handler(func=lambda m: m.text == "Add Email")
def cmd_add(message):
    uid = message.from_user.id
    users = load_users()
    if str(uid) in users and len(users[str(uid)].get("accounts",[])) >= MAX_PER_USER:
        bot.send_message(uid, f"❌ Max {MAX_PER_USER} accounts reached"); return
    user_sessions[uid] = {"step": "add_email"}
    bot.send_message(uid, "Enter your Gmail address:\nExample: example@gmail.com")

@bot.message_handler(func=lambda m: m.text == "My Stats")
def cmd_stats(message):
    uid = message.from_user.id
    users = load_users()
    if str(uid) not in users: bot.send_message(uid, "Not registered yet"); return
    u = users[str(uid)]
    accs = u.get("accounts",[])
    total = sum(a.get("total_emails",0) for a in accs)
    active = sum(1 for a in accs if f"{uid}_{a['email']}" in monitor.active)
    ch = u.get("forward_channel", "DM")
    bot.send_message(uid, f"📊 Your Stats\n\n👤 {u.get('name','')}\n📧 Accounts: {len(accs)}/{MAX_PER_USER}\n🔔 Active: {active}\n📨 Total emails: {total}\n📢 Channel: {ch}", reply_markup=user_menu(uid))

@bot.message_handler(func=lambda m: m.text == "My Accounts")
def cmd_accounts(message):
    uid = message.from_user.id
    users = load_users()
    if str(uid) not in users or not users[str(uid)].get("accounts"):
        bot.send_message(uid, "No accounts yet"); return
    accs = users[str(uid)]["accounts"]
    txt = f"📋 Your Accounts ({len(accs)}/{MAX_PER_USER})\n\n"
    mk = InlineKeyboardMarkup()
    for i, a in enumerate(accs):
        st = "🟢" if f"{uid}_{a['email']}" in monitor.active else "🔴"
        pr = "🔒" if a.get("is_hidden") else "👁"
        txt += f"{i+1}. {st}{pr} {a['email']} | 📨 {a.get('total_emails',0)}\n"
        lbl = "Show" if a.get("is_hidden") else "Hide"
        mk.add(InlineKeyboardButton(f"{lbl}: {a['email'][:20]}", callback_data=f"priv_{i}"))
    txt += "\n🔒=Hidden from admin | 👁=Visible"
    bot.send_message(uid, txt, reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "Delete Account")
def cmd_delete(message):
    uid = message.from_user.id
    users = load_users()
    if str(uid) not in users or not users[str(uid)].get("accounts"):
        bot.send_message(uid, "No accounts"); return
    mk = InlineKeyboardMarkup()
    for i, a in enumerate(users[str(uid)]["accounts"]):
        mk.add(InlineKeyboardButton(f"🗑 {a['email']}", callback_data=f"del_{i}"))
    mk.add(InlineKeyboardButton("Cancel", callback_data="cancel"))
    bot.send_message(uid, "Select account to delete:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "Admin")
def cmd_admin(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, "⛔ Admin only"); return
    user_sessions[uid] = {"step": "admin_pass"}
    bot.send_message(uid, "👑 Enter admin password:")

@bot.message_handler(func=lambda m: m.text == "Refresh")
def cmd_refresh(message):
    cmd_start(message)

@bot.message_handler(func=lambda m: m.text == "Logout Admin")
def cmd_logout(message):
    uid = message.from_user.id
    user_sessions.pop(uid, None)
    bot.send_message(uid, "✅ Logged out of admin", reply_markup=user_menu(uid))

@bot.message_handler(func=lambda m: m.text == "All Users")
def cmd_all_users(message):
    uid = message.from_user.id
    if uid != ADMIN_ID: bot.send_message(uid, "⛔ Admin only"); return
    users = load_users()
    if not users: bot.send_message(uid, "No users yet"); return
    txt = "👥 All Users\n\n"
    for u, d in users.items():
        accs = d.get("accounts",[])
        vis = [a for a in accs if not a.get("is_hidden")]
        hid = len(accs) - len(vis)
        ch = d.get("forward_channel", "DM")
        txt += f"👤 {d.get('name','?')} | ID: {u}\n📧 {len(vis)} visible"
        if hid: txt += f" (+{hid} 🔒)"
        txt += f" | 📢 {ch} | 📨 {sum(a.get('total_emails',0) for a in accs)}\n\n"
    bot.send_message(uid, txt, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "All Accounts")
def cmd_all_accs(message):
    uid = message.from_user.id
    if uid != ADMIN_ID: return
    users = load_users()
    txt = "📧 All Accounts\n\n"
    c = h = 0
    for u, d in users.items():
        for a in d.get("accounts",[]):
            if a.get("is_hidden"): h+=1; continue
            c+=1
            txt += f"{c}. {a['email']} | {d.get('name','?')} | 📨{a.get('total_emails',0)}\n"
    if h: txt += f"\n🔒 {h} hidden accounts"
    txt += f"\n\nTotal: {c} visible + {h} hidden = {c+h}/{MAX_ACCOUNTS}"
    bot.send_message(uid, txt, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "Broadcast")
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    user_sessions[message.from_user.id] = {"step": "broadcast"}
    bot.send_message(message.from_user.id, "Type broadcast message:")

@bot.message_handler(func=lambda m: m.text == "System Stats")
def cmd_sys_stats(message):
    uid = message.from_user.id
    if uid != ADMIN_ID: return
    users = load_users()
    hidden = sum(1 for u in users.values() for a in u.get("accounts",[]) if a.get("is_hidden"))
    with_channel = sum(1 for u in users.values() if u.get("forward_channel"))
    txt = (f"📈 System Stats\n\n"
           f"👥 Users: {len(users)}\n"
           f"📧 Accounts: {sum(len(u.get('accounts',[])) for u in users.values())}/{MAX_ACCOUNTS}\n"
           f"🔔 Active monitors: {len(monitor.active)}\n"
           f"📨 Total emails: {sum(a.get('total_emails',0) for u in users.values() for a in u.get('accounts',[]))}\n"
           f"📢 Users with channels: {with_channel}\n"
           f"🔒 Hidden: {hidden}\n"
           f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    bot.send_message(uid, txt, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "Ban Manager")
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID: return
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("🚫 Ban User", callback_data="ban"), InlineKeyboardButton("✅ Unban", callback_data="unban"), InlineKeyboardButton("📋 Banned List", callback_data="banned_list"))
    bot.send_message(message.from_user.id, "🚫 Ban Management", reply_markup=mk)

# ── Text handler ──────────────────────────────────────────────

@bot.message_handler(content_types=['text'])
def handle_text(message):
    uid = message.from_user.id
    txt = message.text.strip()
    print(f"[text] {uid}: {txt}", flush=True)
    
    if uid not in user_sessions:
        bot.send_message(uid, "Use the buttons below", reply_markup=user_menu(uid)); return
    
    s = user_sessions[uid]
    
    if s.get("step") == "set_channel":
        del user_sessions[uid]
        users = load_users()
        if str(uid) not in users:
            users[str(uid)] = {"name": message.from_user.first_name or "", "register_date": datetime.now().isoformat(), "is_banned": False, "accounts": []}
        
        if txt.lower() == "dm":
            users[str(uid)].pop("forward_channel", None)
            save_users(users)
            bot.send_message(uid, "✅ Emails will be sent to your DMs", reply_markup=user_menu(uid))
        else:
            # Validate channel ID format
            try:
                channel_id = int(txt)
                # Test sending a message to the channel
                try:
                    bot.send_message(channel_id, "✅ Gmail Forwarder connected! Emails will appear here.")
                    users[str(uid)]["forward_channel"] = str(channel_id)
                    save_users(users)
                    bot.send_message(uid, f"✅ Channel set to {channel_id}\n\nAll your emails will now forward there.", reply_markup=user_menu(uid))
                except Exception as e:
                    bot.send_message(uid, f"❌ Can't send to that channel.\n\nMake sure:\n1. The bot is added as admin\n2. The ID is correct\n\nError: {e}", reply_markup=user_menu(uid))
            except ValueError:
                bot.send_message(uid, "❌ Invalid ID. Must be a number (e.g. -1001234567890) or 'dm'", reply_markup=user_menu(uid))
    
    elif s.get("step") == "add_email":
        if "@gmail.com" not in txt.lower():
            bot.send_message(uid, "❌ Must be a Gmail address"); return
        user_sessions[uid] = {"step": "add_pass", "email": txt.lower().strip()}
        bot.send_message(uid, "🔐 Enter your Gmail app password:")
    
    elif s.get("step") == "add_pass":
        addr = s["email"]
        pwd = txt
        try: bot.delete_message(uid, message.message_id)
        except: pass
        try:
            m = imaplib.IMAP4_SSL("imap.gmail.com", timeout=10)
            m.login(addr, pwd); m.select("inbox"); m.logout()
            users = load_users()
            if str(uid) not in users:
                users[str(uid)] = {"name": message.from_user.first_name or "", "register_date": datetime.now().isoformat(), "is_banned": False, "accounts": []}
            users[str(uid)]["accounts"].append({"email":addr,"app_password":pwd,"total_emails":0,"last_email_time":None,"added_date":datetime.now().isoformat(),"is_active":True,"is_hidden":False})
            save_users(users)
            del user_sessions[uid]
            ch = get_user_channel(uid)
            ch_txt = f"📢 Forwarding to: {ch}" if ch else "📢 Forwarding to: your DMs"
            mk = InlineKeyboardMarkup()
            mk.add(InlineKeyboardButton("🔒 Hide from admin", callback_data=f"hide_{addr}"), InlineKeyboardButton("👁 Visible", callback_data=f"vis_{addr}"))
            bot.send_message(uid, f"🎉 Added {addr}!\n\n⚡ Monitoring active\n{ch_txt}\n\n🔐 Privacy:", reply_markup=mk)
            monitor.start(uid, addr, pwd)
        except Exception as e:
            print(f"Login failed: {e}", flush=True)
            bot.send_message(uid, "❌ Connection failed.\n\nCheck:\n- App password is correct\n- IMAP is enabled in Gmail settings")
    
    elif s.get("step") == "admin_pass":
        try: bot.delete_message(uid, message.message_id)
        except: pass
        if txt == ADMIN_PASSWORD and uid == ADMIN_ID:
            user_sessions[uid] = {"admin": True}
            bot.send_message(uid, "👑 Welcome to Admin Panel", reply_markup=admin_menu())
        else:
            bot.send_message(uid, "❌ Wrong password", reply_markup=user_menu(uid))
            user_sessions.pop(uid, None)
    
    elif s.get("step") == "broadcast" and uid == ADMIN_ID:
        users = load_users()
        sent = 0
        for u in users:
            if int(u) != uid and not users[u].get("is_banned"):
                try: bot.send_message(int(u), f"🔔 Admin Notice\n\n{txt}"); sent+=1
                except: pass
        user_sessions.pop(uid, None)
        bot.send_message(uid, f"✅ Sent to {sent} users", reply_markup=admin_menu())
    
    elif s.get("step") == "ban_input":
        users = load_users()
        if txt in users:
            users[txt]["is_banned"] = True; save_users(users)
            monitor.stop_all(int(txt))
            bot.send_message(uid, f"✅ Banned {txt}", reply_markup=admin_menu())
        else: bot.send_message(uid, "❌ User not found", reply_markup=admin_menu())
        user_sessions.pop(uid, None)
    
    elif s.get("step") == "unban_input":
        users = load_users()
        if txt in users:
            users[txt]["is_banned"] = False; save_users(users)
            for a in users[txt].get("accounts",[]):
                if a.get("is_active",True): monitor.start(int(txt), a["email"], a["app_password"])
            bot.send_message(uid, f"✅ Unbanned {txt}", reply_markup=admin_menu())
        else: bot.send_message(uid, "❌ User not found", reply_markup=admin_menu())
        user_sessions.pop(uid, None)

# ── Callbacks ─────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = call.from_user.id
    d = call.data
    
    if d.startswith("del_"):
        i = int(d[4:])
        users = load_users()
        if str(uid) in users:
            accs = users[str(uid)].get("accounts",[])
            if 0<=i<len(accs):
                rm = accs.pop(i); save_users(users)
                monitor.stop(uid, rm["email"])
                bot.send_message(uid, f"✅ Deleted {rm['email']}", reply_markup=user_menu(uid))
    
    elif d.startswith("priv_"):
        i = int(d[5:])
        users = load_users()
        if str(uid) in users:
            accs = users[str(uid)].get("accounts",[])
            if 0<=i<len(accs):
                accs[i]["is_hidden"] = not accs[i].get("is_hidden",False)
                save_users(users)
                st = "🔒 Hidden" if accs[i]["is_hidden"] else "👁 Visible"
                bot.send_message(uid, f"✅ {accs[i]['email']} is now {st}", reply_markup=user_menu(uid))
    
    elif d.startswith("hide_"):
        addr = d[5:]
        users = load_users()
        if str(uid) in users:
            for a in users[str(uid)].get("accounts",[]):
                if a["email"]==addr: a["is_hidden"]=True; save_users(users); break
        bot.send_message(uid, f"🔒 {addr} hidden from admin", reply_markup=user_menu(uid))
    
    elif d.startswith("vis_"):
        addr = d[4:]
        users = load_users()
        if str(uid) in users:
            for a in users[str(uid)].get("accounts",[]):
                if a["email"]==addr: a["is_hidden"]=False; save_users(users); break
        bot.send_message(uid, f"👁 {addr} visible to admin", reply_markup=user_menu(uid))
    
    elif d == "ban":
        if uid != ADMIN_ID: return
        user_sessions[uid] = {"step":"ban_input"}
        bot.send_message(uid, "Enter user ID to ban:")
    
    elif d == "unban":
        if uid != ADMIN_ID: return
        user_sessions[uid] = {"step":"unban_input"}
        bot.send_message(uid, "Enter user ID to unban:")
    
    elif d == "banned_list":
        if uid != ADMIN_ID: return
        users = load_users()
        banned = {u:dd for u,dd in users.items() if dd.get("is_banned")}
        if not banned: bot.send_message(uid, "No banned users", reply_markup=admin_menu())
        else:
            txt = "🚫 Banned Users\n\n"
            for u,dd in banned.items():
                txt += f"ID: {u} | {dd.get('name','?')} | {len(dd.get('accounts',[]))} accounts\n"
            bot.send_message(uid, txt, reply_markup=admin_menu())
    
    elif d == "cancel":
        bot.send_message(uid, "Cancelled", reply_markup=user_menu(uid))
    
    try: bot.answer_callback_query(call.id)
    except: pass

# ── Init & Run ────────────────────────────────────────────────

def init():
    users = load_users()
    for u, d in users.items():
        if d.get("is_banned"): continue
        for a in d.get("accounts",[]):
            if a.get("is_active",True):
                monitor.start(int(u), a["email"], a["app_password"])
    print(f"Users: {len(users)} | Monitors: {len(monitor.active)}", flush=True)

if __name__ == "__main__":
    init()
    bot.remove_webhook()
    time.sleep(1)
    print("Bot V3 running!", flush=True)
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(5)
