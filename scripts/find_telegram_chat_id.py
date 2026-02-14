#!/usr/bin/env python3
"""Find the correct Telegram group chat ID."""
import os
import requests

TOKEN = os.environ.get("IFDS_TELEGRAM_BOT_TOKEN", "8058925472:AAFKeC0_pc-88gG9pgZryIx4wMzMRgofkmA")

r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=5)
data = r.json()

if not data.get("result"):
    print("Nincs update — írj egy üzenetet a group chat-be ahol a bot tag, aztán futtasd újra!")
else:
    seen = set()
    for update in data["result"]:
        msg = update.get("message") or update.get("my_chat_member", {}).get("chat")
        if msg:
            chat = msg.get("chat", msg) if "chat" in msg else msg
            chat_id = chat.get("id")
            chat_type = chat.get("type")
            title = chat.get("title") or chat.get("first_name", "?")
            key = str(chat_id)
            if key not in seen:
                seen.add(key)
                print(f"Chat ID: {chat_id}  Type: {chat_type}  Name: {title}")
