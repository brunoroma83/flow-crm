import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from .config import get_settings


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    derived = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1)
    return f"scrypt${salt}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, stored: str) -> bool:
    _, salt, _ = stored.split("$", 2)
    return hmac.compare_digest(hash_password(password, salt), stored)


def create_token(user_id: int) -> str:
    payload = {"sub": user_id, "exp": int((datetime.now(UTC) + timedelta(hours=12)).timestamp())}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(get_settings().secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def token_subject(token: str) -> int | None:
    try:
        raw, signature = token.split(".", 1)
        expected = hmac.new(get_settings().secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        return int(payload["sub"]) if payload["exp"] > datetime.now(UTC).timestamp() else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def hash_api_key(raw_key: str) -> str:
    """Calcula o hash SHA-256 seguro da chave crua para persistência e busca."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Gera uma nova chave de API segura no formato fc_live_<hex>.
    
    Retorna uma tupla contendo:
    - raw_key: chave completa (exibida apenas uma vez ao usuário/admin)
    - key_prefix: prefixo visível para identificação futura (ex: 'fc_live_a1b2c3')
    - hashed_key: hash SHA-256 para ser salvo no banco
    """
    token = secrets.token_hex(24)
    raw_key = f"fc_live_{token}"
    key_prefix = raw_key[:14]
    hashed_key = hash_api_key(raw_key)
    return raw_key, key_prefix, hashed_key

