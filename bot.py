"""Gmail Forwarder Bot — main entry point."""

import time
import telebot
from config import BOT_TOKEN
from storage import load_users
from monitor import Monitor
from handlers import register_handlers


def main():
    print("Starting Gmail Forwarder Bot...", flush=True)

    bot = telebot.TeleBot(BOT_TOKEN)
    monitor = Monitor(bot)

    # Register all command/text/callback handlers
    register_handlers(bot, monitor)

    # Start monitoring for all active accounts
    users = load_users()
    for uid, data in users.items():
        if data.get("is_banned"):
            continue
        for acc in data.get("accounts", []):
            if acc.get("is_active", True):
                monitor.start(int(uid), acc["email"], acc["app_password"])

    print(f"Users: {len(users)} | Monitors: {len(monitor.active)}", flush=True)

    # Run bot
    bot.remove_webhook()
    time.sleep(1)
    print("Bot running!", flush=True)

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Polling error: {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
