"""OAuth helpers for Weight x Reps."""

import base64
import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

AUTH_ENDPOINT = "https://weightxreps.net/api/auth"


@dataclass(frozen=True)
class PkcePair:
    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str


def generate_pkce_pair() -> PkcePair:
    verifier = secrets.token_urlsafe(48)[:64]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return PkcePair(code_verifier=verifier, code_challenge=challenge)


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
) -> str:
    query = urlencode(
        {
            "grant_type": "authorization_code",
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{AUTH_ENDPOINT}?{query}"


def save_tokens(path: Path, tokens: TokenSet) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(tokens), indent=2), encoding="utf-8")
    path.chmod(0o600)


def load_tokens(path: Path) -> TokenSet | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        token_type=data.get("token_type", "Bearer"),
    )
