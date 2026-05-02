"""Registration captcha and email-code helpers."""

from __future__ import annotations

import base64
import secrets
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

CAPTCHA_TTL_SECONDS = 300
EMAIL_CODE_TTL_SECONDS = 600
MAX_VERIFICATION_ATTEMPTS = 5
CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def hash_verification_code(code: str) -> str:
    return sha256(_normalize_code(code).encode("utf-8")).hexdigest()


def verification_code_matches(code: str, code_hash: str) -> bool:
    return secrets.compare_digest(hash_verification_code(code), code_hash)


def generate_captcha_code(length: int = 5) -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(length))


def generate_email_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def render_captcha_data_url(code: str) -> str:
    image = Image.new("RGB", (180, 64), "#f8fafc")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32)
    for index, char in enumerate(code):
        draw.text((20 + index * 28, 15 + (index % 2) * 4), char, fill="#1f2937", font=font)
    for _ in range(18):
        x1 = secrets.randbelow(180)
        y1 = secrets.randbelow(64)
        x2 = secrets.randbelow(180)
        y2 = secrets.randbelow(64)
        draw.line((x1, y1, x2, y2), fill="#cbd5e1", width=1)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def is_expired(expires_at: datetime) -> bool:
    return expires_at <= datetime.now(UTC)


def _normalize_code(code: str) -> str:
    return "".join(code.strip().upper().split())
