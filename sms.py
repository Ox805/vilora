"""SMS notification system using Twilio."""
import os
import sys
import random


def _get_client():
    """Get Twilio client, or None if not configured."""
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    if not account_sid or not auth_token:
        return None
    try:
        from twilio.rest import Client
        return Client(account_sid, auth_token)
    except ImportError:
        sys.stderr.write("[Vilora] Twilio package not installed. SMS disabled.\n")
        return None


def send_sms(to_number, body):
    """Send an SMS via Twilio. Returns True on success."""
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')
    client = _get_client()

    if not client or not from_number:
        sys.stderr.write(f"[Vilora] Twilio not configured. SMS to {to_number}: {body}\n")
        return False

    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        sys.stderr.write(f"[Vilora] SMS sent to {to_number} (sid {message.sid})\n")
        return message.status in ('queued', 'sent', 'delivered')
    except Exception as e:
        sys.stderr.write(f"[Vilora] SMS send failed to {to_number}: {e}\n")
        return False


def generate_verification_code():
    """Generate a 6-digit verification code."""
    return str(random.randint(100000, 999999))


def send_verification_sms(to_number, code):
    """Send a phone verification code via SMS."""
    body = f"Your Vilora verification code is: {code}. It expires in 10 minutes."
    return send_sms(to_number, body)


def send_activity_sms(to_number, topic, session_link):
    """Send a session activity notification via SMS. Kept under 160 chars."""
    # Truncate topic if needed to stay under 160 chars
    max_topic_len = 60
    truncated_topic = topic[:max_topic_len] + '...' if len(topic) > max_topic_len else topic
    body = f'Vilora: New activity in your session about "{truncated_topic}". Open when you\'re ready: {session_link}'
    return send_sms(to_number, body)
