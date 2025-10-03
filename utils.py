# utils.py
import bcrypt
import uuid
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

SESSION_FILE = Path.home() / ".ecology_cli_session"

def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt())

def check_password(plain: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed)

def create_token() -> str:
    return uuid.uuid4().hex

def save_session_token(token: str):
    SESSION_FILE.write_text(json.dumps({"token": token}))

def load_session_token() -> Optional[str]:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text())
        return data.get("token")
    except Exception:
        return None

def clear_session():
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()

def iso_now():
    return datetime.utcnow().isoformat()

def iso_days_from_now(days: int):
    return (datetime.utcnow() + timedelta(days=days)).date().isoformat()

