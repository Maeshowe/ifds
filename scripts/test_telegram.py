#!/usr/bin/env python3
"""Quick Telegram delivery test."""
import os
import requests

TOKEN = os.environ.get("IFDS_TELEGRAM_BOT_TOKEN", "8058925472:AAFKeC0_pc-88gG9pgZryIx4wMzMRgofkmA")
CHAT_ID = os.environ.get("IFDS_TELEGRAM_CHAT_ID", "-1003660205525")

# Test 1: Bot identity
r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=5)
print(f"Bot info: {r.json()}")

# Test 2: Send test message
msg = "🧪 IFDS Telegram Test\n\nHa ezt látod, a küldés működik!\nTimestamp: " + __import__('datetime').datetime.now().isoformat()
r = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
    timeout=5,
)
print(f"Send result: {r.status_code} — {r.json()}")
