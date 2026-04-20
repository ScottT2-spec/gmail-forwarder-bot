"""Telegram keyboard menus."""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from storage import load_users


def user_menu(uid):
    """Main user keyboard."""
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    users = load_users()
    if str(uid) in users and users[str(uid)].get("accounts"):
        m.add(
            KeyboardButton("Add Email"), KeyboardButton("My Stats"),
            KeyboardButton("My Accounts"), KeyboardButton("Delete Account"),
            KeyboardButton("Set Channel"), KeyboardButton("Refresh")
        )
    else:
        m.add(KeyboardButton("Add Email"), KeyboardButton("Set Channel"))
    if uid == ADMIN_ID:
        m.add(KeyboardButton("Admin"))
    return m


def admin_menu():
    """Admin panel keyboard."""
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        KeyboardButton("All Users"), KeyboardButton("All Accounts"),
        KeyboardButton("Broadcast"), KeyboardButton("System Stats"),
        KeyboardButton("Ban Manager"), KeyboardButton("Logout Admin")
    )
    return m
