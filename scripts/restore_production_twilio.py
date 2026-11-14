#!/usr/bin/env python3
"""Restore Twilio phone number back to production Sabi settings."""

import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+17153122345")

PROD_VOICE_URL = "https://api.eduforequality.org/voice/twilio/incoming"
PROD_STATUS_CALLBACK = "https://eduforequality.org/api/sabi/voice/status"

client = Client(ACCOUNT_SID, AUTH_TOKEN)
numbers = client.incoming_phone_numbers.list(phone_number=PHONE_NUMBER)

if not numbers:
    print(f"Error: Phone number {PHONE_NUMBER} not found on Twilio account.")
    exit(1)

number = numbers[0]
updated = client.incoming_phone_numbers(number.sid).update(
    voice_url=PROD_VOICE_URL,
    voice_method="POST",
    status_callback=PROD_STATUS_CALLBACK,
    status_callback_method="POST",
)

print(f"✅ Successfully restored {updated.phone_number} to production Sabi!")
print(f"   Voice URL: {updated.voice_url}")
print(f"   Status Callback: {updated.status_callback}")

