# Gmail Forwarder Bot 📧

A Telegram bot that monitors Gmail inboxes and forwards new emails to Telegram in real-time.

## Features

- 📧 **Multi-Account** — Up to 5 Gmail accounts per user
- 🔔 **Real-Time Monitoring** — New emails forwarded instantly to Telegram
- 🔒 **Privacy** — Users can hide accounts from admin view
- 👑 **Admin Panel** — User management, stats, broadcast, ban system
- 📊 **Stats Tracking** — Email count, active monitors, per-user metrics
- 🗑 **Account Management** — Add, delete, toggle monitoring

## Setup

### 1. Create a Telegram Bot
- Talk to [@BotFather](https://t.me/BotFather) on Telegram
- Create a new bot and get the token

### 2. Set Environment Variables
```bash
BOT_TOKEN=your_telegram_bot_token
ADMIN_PASSWORD=your_admin_password
```

### 3. Install & Run
```bash
pip install pyTelegramBotAPI
python gmail_v2_clean.py
```

## How It Works

1. User sends `/start` to the bot
2. User adds Gmail account (email + [App Password](https://myaccount.google.com/apppasswords))
3. Bot connects via IMAP and monitors for new emails
4. New emails are forwarded to the user's Telegram chat

## Gmail App Password

Users need a Gmail **App Password** (not their regular password):
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" → "Other" → name it anything
3. Use the 16-character password with the bot

## Admin Features

- **All Users** — View registered users and account counts
- **All Accounts** — View all visible email accounts
- **System Stats** — Total users, accounts, active monitors
- **Broadcast** — Send message to all users
- **Ban Manager** — Ban/unban users

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | Required |
| `ADMIN_PASSWORD` | Admin panel password | Required |
| `ADMIN_ID` | Your Telegram user ID | Set in code |
| `MAX_ACCOUNTS` | Total max accounts | 50 |
| `MAX_PER_USER` | Max accounts per user | 5 |

## Requirements

- Python 3.8+
- `pyTelegramBotAPI`

## Built By

Scott Antwi — [GitHub](https://github.com/ScottT2-spec)
