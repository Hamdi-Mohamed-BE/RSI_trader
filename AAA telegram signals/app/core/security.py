# Simple security module for password hashing and authentication if needed in VPS environments
import secrets

def generate_secret_key() -> str:
    return secrets.token_hex(32)
