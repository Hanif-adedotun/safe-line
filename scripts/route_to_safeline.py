#!/usr/bin/env python3
"""Temporarily route Twilio phone number to SafeLine hackathon demo."""

import sys
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

if len(sys.argv) < 2:
    print("Usage: python route_to_safeline.py <https://your-tunnel-url>")
    exit(1)

tunnel_url = sys.argv[1].rstrip("/")
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+17153122345")

voice_url = f"{tunnel_url}/voice/incoming"

client = Client(ACCOUNT_SID, AUTH_TOKEN)
numbers = client.incoming_phone_numbers.list(phone_number=PHONE_NUMBER)

if not numbers:
    print(f"Error: Phone number {PHONE_NUMBER} not found on Twilio account.")
    exit(1)

number = numbers[0]
updated = client.incoming_phone_numbers(number.sid).update(
    voice_url=voice_url,
    voice_method="POST",
)

print(f"🚀 Temporary Hackathon Routing Active for {updated.phone_number}!")
print(f"   Inbound Voice Webhook -> {updated.voice_url}")

