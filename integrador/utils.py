import json
import base64
from django.core import signing

STATE_SALT = 'integrador-state'

def make_state(payload: dict) -> str:
    signed = signing.dumps(payload, salt=STATE_SALT)
    return base64.urlsafe_b64encode(signed.encode()).decode()

def read_state(value: str) -> dict:
    signed = base64.urlsafe_b64decode(value.encode()).decode()
    return signing.loads(signed, salt=STATE_SALT)
