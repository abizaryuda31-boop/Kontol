# utils.py
import re
import random
import string
import imaplib

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_gmail_valid(email, password):
    try:
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(email, password)
        imap.logout()
        return True
    except:
        return False

def format_rupiah(amount):
    try:
        val = int(amount) if amount is not None else 0
        return f"Rp {val:,.0f}".replace(',', '.')
    except (ValueError, TypeError):
        return "Rp 0"

def is_valid_dana(number):
    return re.match(r'^08[0-9]{8,12}$', number) is not None

def mask_dana(number):
    # Biar jadi 0812****9999
    if len(number) >= 8:
        return number[:4] + "****" + number[-4:]
    return number
