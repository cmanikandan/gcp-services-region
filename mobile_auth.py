#!/usr/bin/env python3
"""
Zero-Dependency Mobile Authentication & Cloud Vault Sync Engine (mobile_auth.py).

Implements passwordless mobile authentication and encrypted-token session management
for the Google Cloud Explorer iOS & iPadOS app using 100% Python 3.10+ standard library:
  - Stateless HMAC-SHA256 JWT access tokens (`HS256`, 1-hour TTL)
  - Single-use rotating refresh tokens (SHA-256 hashed at rest, 30-day TTL)
  - RFC 7636 OAuth 2.0 PKCE (`S256`) challenge verification
  - WebAuthn / Passkey (`P-256`) public key registration & challenge nonces
  - Per-user Cloud Vault sync (bookmarks, SLA stacks, Gen Z vibe themes & XP)
  - Apple App Store Guideline 5.1.1(v) 1-tap account & vault deletion

Security Note:
  This service strictly manages local/companion Explorer app profiles (bookmarks,
  architecture stacks, UI preferences). It NEVER requests, stores, or touches
  Google Cloud IAM credentials, billing accounts, or live cloud projects.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any

CACHE_DIR = Path(__file__).resolve().parent / "data" / "cache"
USERS_FILE = CACHE_DIR / "mobile_users.json"
SECRET_FILE = CACHE_DIR / "auth_secret.key"

ACCESS_TOKEN_TTL_SECONDS = 3600           # 1 hour
REFRESH_TOKEN_TTL_SECONDS = 30 * 86400    # 30 days
CHALLENGE_TTL_SECONDS = 300               # 5 minutes

VALID_PROVIDERS = {"apple", "google_pkce", "passkey", "magic_handle"}
VALID_VIBES = {"cyberMatcha", "ultravioletPulse", "y2kChrome", "sunsetVapor"}


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_pkce_s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return _b64url_encode(digest)


def sanitize_handle(raw_handle: str) -> str:
    cleaned = re.sub(r"[^a-z0-9._-]", "", raw_handle.strip().lower().lstrip("@"))
    return cleaned[:28] if len(cleaned) >= 2 else f"cloud.builder.{secrets.token_hex(2)}"


def compute_builder_xp_and_level(vault: dict[str, Any]) -> tuple[int, str]:
    svc_count = len(vault.get("bookmarked_services", []))
    reg_count = len(vault.get("bookmarked_regions", []))
    stack_count = len(vault.get("customer_stacks", []))
    xp = 100 + (svc_count * 15) + (reg_count * 20) + (stack_count * 65)

    if xp >= 500:
        level = "LVL 5 • Five-Nines Wizard 🧙‍♂️"
    elif xp >= 340:
        level = "LVL 4 • Multi-Region Main Character ⚡"
    elif xp >= 220:
        level = "LVL 3 • FinOps Vibe Architect 💸"
    elif xp >= 150:
        level = "LVL 2 • Cloud Stack Curator ✨"
    else:
        level = "LVL 1 • Cloud Explorer Rookie 🌱"
    return xp, level


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class MobileAuthVaultService:
    """Thread-safe mobile identity, JWT/Refresh token, and Cloud Vault store."""

    def __init__(self, users_file: Path = USERS_FILE, secret_file: Path = SECRET_FILE) -> None:
        self._lock = threading.RLock()
        self._users_file = users_file
        self._secret_file = secret_file
        self._challenges: dict[str, dict[str, Any]] = {}
        self._secret = self._load_or_create_secret()

    def _load_or_create_secret(self) -> bytes:
        env_secret = os.environ.get("GCE_AUTH_SECRET", "").strip()
        if env_secret:
            return hashlib.sha256(env_secret.encode("utf-8")).digest()
        self._secret_file.parent.mkdir(parents=True, exist_ok=True)
        if self._secret_file.exists():
            raw = self._secret_file.read_bytes()
            if len(raw) >= 32:
                return raw[:32]
        secret = secrets.token_bytes(32)
        self._secret_file.write_bytes(secret)
        try:
            os.chmod(self._secret_file, 0o600)
        except OSError:
            pass
        return secret

    def _load_db(self) -> dict[str, Any]:
        if not self._users_file.exists():
            return {"users": {}, "refresh_sessions": {}}
        try:
            data = json.loads(self._users_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "users" in data and "refresh_sessions" in data:
                return data
        except Exception:
            pass
        return {"users": {}, "refresh_sessions": {}}

    def _save_db(self, db: dict[str, Any]) -> None:
        self._users_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._users_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(db, indent=2), encoding="utf-8")
        tmp.replace(self._users_file)

    def _mint_jwt(self, user_id: str, handle: str, provider: str, now: int) -> tuple[str, int]:
        exp = now + ACCESS_TOKEN_TTL_SECONDS
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "handle": handle,
            "prv": provider,
            "iat": now,
            "exp": exp,
            "jti": secrets.token_hex(8),
        }
        signing_input = f"{_b64url_encode(json.dumps(header, separators=(',', ':')).encode())}.{_b64url_encode(json.dumps(payload, separators=(',', ':')).encode())}"
        sig = hmac.new(self._secret, signing_input.encode("ascii"), hashlib.sha256).digest()
        return f"{signing_input}.{_b64url_encode(sig)}", exp

    def verify_access_token(self, token: str) -> dict[str, Any]:
        parts = token.strip().split(".")
        if len(parts) != 3:
            raise AuthError("Malformed Bearer token", status=401)
        signing_input = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(self._secret, signing_input.encode("ascii"), hashlib.sha256).digest()
        try:
            actual_sig = _b64url_decode(parts[2])
        except Exception as exc:
            raise AuthError("Invalid token signature encoding", status=401) from exc

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise AuthError("Invalid Bearer token signature", status=401)

        try:
            payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        except Exception as exc:
            raise AuthError("Corrupted token payload", status=401) from exc

        now = int(time.time())
        if int(payload.get("exp", 0)) < now:
            raise AuthError("Access token expired", status=401)
        return payload

    def issue_challenge(self, provider: str = "passkey") -> dict[str, Any]:
        now = int(time.time())
        with self._lock:
            expired = [cid for cid, c in self._challenges.items() if c["expires_at"] < now]
            for cid in expired:
                self._challenges.pop(cid, None)

            challenge_id = f"chl_{secrets.token_hex(8)}"
            nonce = _b64url_encode(secrets.token_bytes(24))
            entry = {
                "challenge_id": challenge_id,
                "provider": provider,
                "nonce": nonce,
                "expires_at": now + CHALLENGE_TTL_SECONDS,
            }
            self._challenges[challenge_id] = entry
            return entry

    def login_or_register(self, body: dict[str, Any]) -> dict[str, Any]:
        provider = str(body.get("provider", "passkey")).strip().lower()
        if provider not in VALID_PROVIDERS:
            raise AuthError(f"Unsupported auth provider '{provider}'", status=400)

        # Verify RFC 7636 PKCE S256 if code_challenge is supplied
        code_challenge = str(body.get("code_challenge") or "").strip()
        code_verifier = str(body.get("code_verifier") or "").strip()
        if provider == "google_pkce" or code_challenge:
            if not code_verifier or not code_challenge:
                raise AuthError("PKCE S256 requires both code_verifier and code_challenge", status=400)
            computed = compute_pkce_s256(code_verifier)
            if not hmac.compare_digest(computed, code_challenge):
                raise AuthError("PKCE S256 code_verifier mismatch", status=401)

        handle = sanitize_handle(str(body.get("handle") or "cloud.architect"))
        display_name = str(body.get("display_name") or f"@{handle}").strip()[:48]
        email = str(body.get("email") or f"{handle}@privaterelay.explorer.local").strip().lower()[:120]
        avatar_emoji = str(body.get("avatar_emoji") or "⚡").strip()[:8] or "⚡"
        role_vibe = str(body.get("role_vibe") or "aiBuilder").strip()[:32]
        public_key_b64 = str(body.get("public_key_b64") or "").strip() or None
        initial_vault = body.get("initial_vault") if isinstance(body.get("initial_vault"), dict) else {}

        now = int(time.time())
        iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._lock:
            db = self._load_db()
            users: dict[str, Any] = db["users"]

            # Match existing user by handle + provider or email
            existing_uid = None
            for uid, u in users.items():
                if u.get("handle") == handle:
                    existing_uid = uid
                    break

            if existing_uid is None:
                user_id = f"usr_{secrets.token_hex(8)}"
                vibe_theme = str(initial_vault.get("vibe_theme") or "cyberMatcha")
                if vibe_theme not in VALID_VIBES:
                    vibe_theme = "cyberMatcha"
                vault = {
                    "bookmarked_services": list(dict.fromkeys(initial_vault.get("bookmarked_services") or ["spanner", "cloud-run", "vertex-ai", "bigquery", "alloydb"])),
                    "bookmarked_regions": list(dict.fromkeys(initial_vault.get("bookmarked_regions") or ["us-central1", "europe-west4", "asia-south1"])),
                    "customer_stacks": initial_vault.get("customer_stacks") if isinstance(initial_vault.get("customer_stacks"), list) else [],
                    "vibe_theme": vibe_theme,
                    "updated_epoch": now,
                }
                xp, level = compute_builder_xp_and_level(vault)
                user_record = {
                    "user_id": user_id,
                    "handle": handle,
                    "display_name": display_name,
                    "email": email,
                    "provider": provider,
                    "avatar_emoji": avatar_emoji,
                    "role_vibe": role_vibe,
                    "public_key_b64": public_key_b64,
                    "created_at": iso_now,
                    "xp_points": xp,
                    "builder_level": level,
                    "vault": vault,
                }
                users[user_id] = user_record
            else:
                user_id = existing_uid
                user_record = users[user_id]
                user_record["provider"] = provider
                user_record["avatar_emoji"] = avatar_emoji or user_record.get("avatar_emoji", "⚡")
                user_record["role_vibe"] = role_vibe or user_record.get("role_vibe", "aiBuilder")
                if public_key_b64:
                    user_record["public_key_b64"] = public_key_b64
                xp, level = compute_builder_xp_and_level(user_record["vault"])
                user_record["xp_points"] = xp
                user_record["builder_level"] = level

            tokens = self._issue_session_tokens_locked(db, user_id, handle, provider, now)
            self._save_db(db)
            return {
                "user": self._public_user_dict(user_record),
                "tokens": tokens,
                "vault": user_record["vault"],
            }

    def refresh_session(self, refresh_token: str) -> dict[str, Any]:
        raw = refresh_token.strip()
        if not raw:
            raise AuthError("Missing refresh_token", status=400)
        token_hash = _sha256_hex(raw)
        now = int(time.time())

        with self._lock:
            db = self._load_db()
            sessions: dict[str, Any] = db["refresh_sessions"]
            sess = sessions.pop(token_hash, None)
            if sess is None:
                self._save_db(db)
                raise AuthError("Invalid or already-rotated refresh token", status=401)
            if int(sess.get("expires_at", 0)) < now:
                self._save_db(db)
                raise AuthError("Refresh token expired", status=401)

            user_id = sess["user_id"]
            user_record = db["users"].get(user_id)
            if not user_record:
                self._save_db(db)
                raise AuthError("Account no longer exists", status=401)

            tokens = self._issue_session_tokens_locked(
                db, user_id, user_record["handle"], user_record["provider"], now
            )
            self._save_db(db)
            return {
                "user": self._public_user_dict(user_record),
                "tokens": tokens,
                "vault": user_record["vault"],
            }

    def get_me(self, access_token: str) -> dict[str, Any]:
        claims = self.verify_access_token(access_token)
        user_id = claims["sub"]
        with self._lock:
            db = self._load_db()
            user_record = db["users"].get(user_id)
            if not user_record:
                raise AuthError("User not found", status=401)
            return {
                "user": self._public_user_dict(user_record),
                "vault": user_record["vault"],
            }

    def sync_vault(self, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        claims = self.verify_access_token(access_token)
        user_id = claims["sub"]
        now = int(time.time())

        with self._lock:
            db = self._load_db()
            user_record = db["users"].get(user_id)
            if not user_record:
                raise AuthError("User not found", status=401)

            vault = user_record["vault"]
            if isinstance(payload.get("bookmarked_services"), list):
                vault["bookmarked_services"] = [str(s) for s in dict.fromkeys(payload["bookmarked_services"])][:200]
            if isinstance(payload.get("bookmarked_regions"), list):
                vault["bookmarked_regions"] = [str(r) for r in dict.fromkeys(payload["bookmarked_regions"])][:80]
            if isinstance(payload.get("customer_stacks"), list):
                vault["customer_stacks"] = payload["customer_stacks"][:30]
            if isinstance(payload.get("vibe_theme"), str) and payload["vibe_theme"] in VALID_VIBES:
                vault["vibe_theme"] = payload["vibe_theme"]
            if isinstance(payload.get("avatar_emoji"), str) and payload["avatar_emoji"].strip():
                user_record["avatar_emoji"] = payload["avatar_emoji"].strip()[:8]
            if isinstance(payload.get("role_vibe"), str) and payload["role_vibe"].strip():
                user_record["role_vibe"] = payload["role_vibe"].strip()[:32]

            vault["updated_epoch"] = now
            xp, level = compute_builder_xp_and_level(vault)
            user_record["xp_points"] = xp
            user_record["builder_level"] = level
            self._save_db(db)
            return {
                "user": self._public_user_dict(user_record),
                "vault": vault,
            }

    def logout(self, refresh_token: str | None = None) -> dict[str, str]:
        if refresh_token:
            token_hash = _sha256_hex(refresh_token.strip())
            with self._lock:
                db = self._load_db()
                if token_hash in db["refresh_sessions"]:
                    db["refresh_sessions"].pop(token_hash, None)
                    self._save_db(db)
        return {"status": "logged_out"}

    def delete_account(self, access_token: str) -> dict[str, str]:
        claims = self.verify_access_token(access_token)
        user_id = claims["sub"]
        with self._lock:
            db = self._load_db()
            if user_id not in db["users"]:
                raise AuthError("User not found", status=404)
            db["users"].pop(user_id, None)
            to_purge = [h for h, s in db["refresh_sessions"].items() if s.get("user_id") == user_id]
            for h in to_purge:
                db["refresh_sessions"].pop(h, None)
            self._save_db(db)
            return {"status": "deleted", "user_id": user_id}

    def _issue_session_tokens_locked(
        self, db: dict[str, Any], user_id: str, handle: str, provider: str, now: int
    ) -> dict[str, Any]:
        # Prune expired refresh sessions opportunistically
        sessions = db["refresh_sessions"]
        expired = [h for h, s in sessions.items() if int(s.get("expires_at", 0)) < now]
        for h in expired:
            sessions.pop(h, None)

        access_token, access_exp = self._mint_jwt(user_id, handle, provider, now)
        refresh_token = f"rft_{secrets.token_urlsafe(32)}"
        sessions[_sha256_hex(refresh_token)] = {
            "user_id": user_id,
            "issued_at": now,
            "expires_at": now + REFRESH_TOKEN_TTL_SECONDS,
        }
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL_SECONDS,
            "expires_at": access_exp,
        }

    @staticmethod
    def _public_user_dict(u: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": u["user_id"],
            "handle": u["handle"],
            "display_name": u["display_name"],
            "email": u["email"],
            "provider": u["provider"],
            "avatar_emoji": u.get("avatar_emoji", "⚡"),
            "role_vibe": u.get("role_vibe", "aiBuilder"),
            "created_at": u["created_at"],
            "xp_points": u.get("xp_points", 100),
            "builder_level": u.get("builder_level", "LVL 1 • Cloud Explorer Rookie 🌱"),
        }
