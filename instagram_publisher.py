#!/usr/bin/env python3
"""
Cooking Clip US - Headless Instagram Reels Publisher
Supports TWO Publishing Methods:
1. Direct Credentials via 2 Env Vars (INSTAGRAM_USERNAME & INSTAGRAM_PASSWORD) - ZERO Meta Developer App needed!
2. Meta Graph API (INSTAGRAM_ACCESS_TOKEN & INSTAGRAM_ACCOUNT_ID)
"""

import json
import os
import pathlib
import sys
import time
from typing import Optional, Dict, Any


def upload_reel_direct(
    video_path: str,
    caption: str,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Uploads directly to Instagram Reels using just 2 env vars (Username + Password). No Meta Developer App needed!"""
    user = username or os.environ.get("INSTAGRAM_USERNAME", "cooked_clips_us")
    pwd = password or os.environ.get("INSTAGRAM_PASSWORD")

    if not user or not pwd:
        return None

    try:
        from instagrapi import Client
        print(f"[*] Logging directly into Instagram as @{user} (No Meta App needed)...")
        cl = Client()
        
        # Load session if exists, otherwise login
        session_file = pathlib.Path("ig_session.json")
        if session_file.exists():
            try:
                cl.load_settings(session_file)
            except Exception:
                pass
        
        cl.login(user, pwd)
        cl.dump_settings(session_file)
        print(f"[✅ LOGGED IN] Uploading Reel to @{user}...")

        media = cl.clip_upload(pathlib.Path(video_path), caption=caption)
        reel_url = f"https://www.instagram.com/reel/{media.code}/"
        print(f"[🚀 REEL PUBLISHED!] Live URL: {reel_url}")
        return {
            "media_id": media.id,
            "code": media.code,
            "url": reel_url,
            "status": "PUBLISHED"
        }
    except Exception as e:
        print(f"[!] Direct Instagram upload error: {e}")
        return None


def upload_reel_meta_api(
    video_url: str,
    caption: str,
    access_token: Optional[str] = None,
    account_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Uploads via Meta Graph API if token is provided."""
    import urllib.request
    import urllib.parse
    import urllib.error

    token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    ig_id = account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID")

    if not token or not ig_id:
        return None

    api_base = "https://graph.facebook.com/v20.0"
    init_url = f"{api_base}/{ig_id}/media"
    init_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token
    }
    
    try:
        data = urllib.parse.urlencode(init_payload).encode("utf-8")
        req = urllib.request.Request(init_url, data=data)
        with urllib.request.urlopen(req) as resp:
            creation_id = json.loads(resp.read().decode()).get("id")

        if not creation_id:
            return None

        # Poll status
        status_url = f"{api_base}/{creation_id}?fields=status_code&access_token={token}"
        for _ in range(30):
            time.sleep(5)
            with urllib.request.urlopen(status_url) as s_resp:
                if json.loads(s_resp.read().decode()).get("status_code") == "FINISHED":
                    break

        # Publish
        pub_url = f"{api_base}/{ig_id}/media_publish"
        pub_payload = {"creation_id": creation_id, "access_token": token}
        pub_data = urllib.parse.urlencode(pub_payload).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(pub_url, data=pub_data)) as p_resp:
            post_id = json.loads(p_resp.read().decode()).get("id")

        return {"url": f"https://www.instagram.com/reel/{post_id}/", "status": "PUBLISHED"}
    except Exception as e:
        print(f"[!] Meta API Error: {e}")
        return None


def upload_reel(video_path: str, caption: str, video_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Master uploader: Tries Direct 2-Env-Var login first, then Meta API."""
    # 1. Try Direct 2 Env Vars (Username + Password)
    if os.environ.get("INSTAGRAM_PASSWORD"):
        res = upload_reel_direct(video_path, caption)
        if res:
            return res

    # 2. Try Meta API
    if os.environ.get("INSTAGRAM_ACCESS_TOKEN") and (video_url or video_path.startswith("http")):
        return upload_reel_meta_api(video_url or video_path, caption)

    print("[*] No active Instagram publishing credentials found. Staging video locally.")
    return None


if __name__ == "__main__":
    if len(sys.argv) > 2:
        upload_reel(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python instagram_publisher.py <video_path> <caption>")
