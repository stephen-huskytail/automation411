"""
GMB Post Library — shared utilities for all three GMB posting scripts.
Handles: Google OAuth refresh, GBP API posting, image generation,
JPEG conversion, GitHub CDN upload, phone number stripping, dedup guard.
"""

import os
import re
import sys
import json
import time
import base64
import hashlib
import datetime
import subprocess
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path


# ── Google OAuth ──────────────────────────────────────────────────────────────

def get_google_oauth_credentials() -> tuple[str, str, str, str]:
    """Load the preferred OAuth credentials for GBP posting.

    Prefer Stephen's Google account because it owns/manages the Business Profiles;
    fall back to Hermes only for legacy environments.
    """
    choices = [
        ("GMB_GOOGLE", "GMB_GOOGLE_CLIENT_ID", "GMB_GOOGLE_CLIENT_SECRET", "GMB_GOOGLE_REFRESH_TOKEN"),
        ("GBP_GOOGLE", "GBP_GOOGLE_CLIENT_ID", "GBP_GOOGLE_CLIENT_SECRET", "GBP_GOOGLE_REFRESH_TOKEN"),
        ("STEPHEN_GOOGLE", "STEPHEN_GOOGLE_WEB_CLIENT_ID", "STEPHEN_GOOGLE_WEB_CLIENT_SECRET", "STEPHEN_GOOGLE_REFRESH_TOKEN"),
        ("HERMES_GOOGLE", "HERMES_GOOGLE_CLIENT_ID", "HERMES_GOOGLE_CLIENT_SECRET", "HERMES_GOOGLE_REFRESH_TOKEN"),
    ]
    for label, client_key, secret_key, refresh_key in choices:
        client_id = os.environ.get(client_key)
        client_secret = os.environ.get(secret_key)
        refresh_token = os.environ.get(refresh_key)
        if client_id and client_secret and refresh_token:
            return client_id, client_secret, refresh_token, label
    raise RuntimeError(
        "Missing Google OAuth credentials for GBP posting. Expected GMB_GOOGLE_*, "
        "GBP_GOOGLE_*, STEPHEN_GOOGLE_*, or HERMES_GOOGLE_* env vars."
    )

def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Exchange a refresh token for a short-lived access token."""
    url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"OAuth token refresh failed {e.code}: {body}")
    if "access_token" not in data:
        raise RuntimeError(f"No access_token in response: {data}")
    return data["access_token"]


# ── GBP API ───────────────────────────────────────────────────────────────────

GBP_BASE = "https://mybusiness.googleapis.com/v4"
# GBP uses /v4 for localPosts
GBP_V1_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"

def _api_call(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_body = resp.read()
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"GBP API {method} {url} failed {e.code}: {body_text}")


def post_to_gbp(
    token: str,
    account_id: str,
    location_id: str,
    text: str,
    cta_type: str,
    cta_url: str | None,
    media_url: str | None,
) -> dict:
    """Create a LOCAL_POST on a GBP location."""
    parent = f"accounts/{account_id}/locations/{location_id}"
    url = f"{GBP_BASE}/{parent}/localPosts"

    payload: dict = {
        "languageCode": "en-US",
        "summary": text[:1500],  # GBP max
        "topicType": "STANDARD",
    }

    # CTA
    if cta_type == "LEARN_MORE" and cta_url:
        payload["callToAction"] = {"actionType": "LEARN_MORE", "url": cta_url}
    elif cta_type == "CALL":
        payload["callToAction"] = {"actionType": "CALL"}

    # Media
    if media_url:
        payload["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": media_url}]

    return _api_call("POST", url, token, payload)


def preflight_gbp_local_posts(token: str, account_id: str, location_id: str) -> dict:
    """Verify the GBP localPosts endpoint before spending image/API credits."""
    parent = f"accounts/{account_id}/locations/{location_id}"
    url = f"{GBP_BASE}/{parent}/localPosts?pageSize=1"
    return _api_call("GET", url, token)


def list_gbp_local_posts(token: str, account_id: str, location_id: str) -> list[dict]:
    """Return all local posts for a location, following GBP pagination."""
    parent = f"accounts/{account_id}/locations/{location_id}"
    url = f"{GBP_BASE}/{parent}/localPosts?pageSize=100"
    posts: list[dict] = []
    while url:
        result = _api_call("GET", url, token)
        posts.extend(result.get("localPosts", []))
        next_token = result.get("nextPageToken")
        url = f"{GBP_BASE}/{parent}/localPosts?pageSize=100&pageToken={urllib.parse.quote(next_token)}" if next_token else ""
    return posts


def delete_gbp_local_post(token: str, post_name: str) -> None:
    """Permanently delete one exact GBP local-post resource name."""
    if not post_name.startswith("accounts/") or "/localPosts/" not in post_name:
        raise ValueError("post_name must be a full GBP local-post resource name")
    _api_call("DELETE", f"{GBP_BASE}/{post_name}", token)


# ── Phone number stripping ────────────────────────────────────────────────────

_PHONE_RE = re.compile(
    r"(?:\+?1[\s\-.]?)?"           # optional country code
    r"(?:\(?\d{3}\)?[\s\-.]?)"     # area code
    r"\d{3}[\s\-.]?\d{4}"          # local number
)

def strip_phone_numbers(text: str) -> str:
    """Remove any phone number patterns from post text."""
    return _PHONE_RE.sub("", text).strip()


# ── Dedup guard ───────────────────────────────────────────────────────────────

def check_dedup(state: dict, guard_hours: int = 20) -> bool:
    """Return True if safe to post (no post within guard_hours). Updates state."""
    last = state.get("last_post")
    if last:
        last_dt = datetime.datetime.fromisoformat(last)
        elapsed = (datetime.datetime.utcnow() - last_dt).total_seconds() / 3600
        if elapsed < guard_hours:
            print(f"[SKIP] Last post was {elapsed:.1f}h ago — dedup guard ({guard_hours}h). Exiting.")
            return False
    return True


def record_post(state: dict) -> None:
    state["last_post"] = datetime.datetime.utcnow().isoformat()


# ── State persistence ─────────────────────────────────────────────────────────

def load_state(path: str, defaults: dict) -> dict:
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if not isinstance(data, dict):
                raise ValueError("state root must be a JSON object")
            # merge — ensure all defaults are present
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception as exc:
            raise RuntimeError(f"Unable to load GMB state file {path}: {exc}") from exc
    return dict(defaults)


def save_state(path: str, state: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(state, indent=2))


# ── Image generation (OpenAI Image 2) ─────────────────────────────────────────

def generate_image(prompt: str, openai_api_key: str) -> bytes:
    """Generate a wide image via GPT Image 2, return raw JPEG bytes."""
    url = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": "1536x1024",
        "quality": "medium",
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {openai_api_key}")
    req.add_header("Content-Type", "application/json")
    # gpt-image-2 can take >2 min on busy days — 180 s avoids transient timeout kills.
    # Retry once on timeout before giving up.
    result = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read())
            break  # success
        except TimeoutError:
            if attempt == 0:
                continue  # retry once
            raise RuntimeError("DALL-E generation timed out after 2 attempts (180 s each)")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise RuntimeError(f"DALL-E generation failed {e.code}: {body}")
    if result is None:
        raise RuntimeError("DALL-E generation failed: no result returned")

    b64 = result["data"][0]["b64_json"]
    # DALL-E 3 returns PNG — convert to JPEG
    png_bytes = base64.b64decode(b64)
    return convert_to_jpeg(png_bytes)


def convert_to_jpeg(image_bytes: bytes) -> bytes:
    """Convert any image bytes to JPEG using PIL (preferred) or sips fallback."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except ImportError:
        pass

    # fallback: write to tmp file and use sips (macOS) or ImageMagick
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image_bytes)
        src = f.name
    dst = src.replace(".png", ".jpg")
    try:
        result = subprocess.run(
            ["sips", "-s", "format", "jpeg", src, "--out", dst],
            capture_output=True, timeout=30
        )
        if result.returncode == 0:
            data = Path(dst).read_bytes()
            return data
    except FileNotFoundError:
        pass
    finally:
        for p in [src, dst]:
            try:
                os.unlink(p)
            except Exception:
                pass

    raise RuntimeError("Could not convert image to JPEG — install Pillow: pip install Pillow")


# ── GitHub CDN upload ─────────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"

def upload_to_github(
    jpeg_bytes: bytes,
    repo: str,           # e.g. "stephen-huskytail/automation411"
    path_in_repo: str,   # e.g. "gmb/huskytail/gmb-seo_education-20260624-1600.jpg"
    github_token: str,
    commit_message: str = "GMB image auto-upload",
) -> str:
    """Upload JPEG to GitHub, return raw.githubusercontent.com CDN URL."""
    github_token = github_token.strip()
    b64_content = base64.b64encode(jpeg_bytes).decode()
    api_url = f"{GITHUB_API}/repos/{repo}/contents/{path_in_repo}"

    # Check if file already exists (to get SHA for update)
    # Retry once on transient GitHub 5xx (e.g. 502 Bad Gateway)
    sha = None
    req = urllib.request.Request(api_url, method="GET")
    req.add_header("Authorization", f"token {github_token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    _last_err: urllib.error.HTTPError | None = None
    for _attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                existing = json.loads(resp.read())
                sha = existing.get("sha")
            _last_err = None
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break  # file doesn't exist yet — that's fine
            if e.code >= 500 and _attempt == 0:
                import time as _time
                _time.sleep(5)
                _last_err = e
                continue  # retry once on 5xx
            raise
    if _last_err is not None:
        raise _last_err

    payload: dict = {
        "message": commit_message,
        "content": b64_content,
    }
    if sha:
        payload["sha"] = sha

    data = json.dumps(payload).encode()
    req = urllib.request.Request(api_url, data=data, method="PUT")
    req.add_header("Authorization", f"token {github_token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"GitHub upload failed {e.code}: {body}")

    # Build CDN URL
    branch = result.get("content", {}).get("html_url", "").split("/blob/")[1].split("/")[0] if "content" in result else "main"
    cdn_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path_in_repo}"
    return cdn_url


# ── Google Drive image download (Texas Tows) ─────────────────────────────────

def list_drive_files(folder_id: str, token: str) -> list[dict]:
    """List files in a Google Drive folder."""
    url = (
        "https://www.googleapis.com/drive/v3/files"
        f"?q=%27{folder_id}%27+in+parents+and+trashed%3Dfalse"
        "&fields=files(id,name,mimeType)&pageSize=100"
    )
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("files", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Drive list failed {e.code}: {body}")


def download_drive_file(file_id: str, token: str) -> bytes:
    """Download a Drive file by ID."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Drive download failed {e.code}: {body}")
