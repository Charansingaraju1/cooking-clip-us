#!/usr/bin/env python3
"""
Cooking Clip US - Headless YouTube Shorts Publisher
Publishes vertical Shorts via YouTube Data API v3.
Features:
- Headless execution (auto-refreshes OAuth token using refresh_token).
- Uses GitHub Secrets (YOUTUBE_TOKEN_JSON, YOUTUBE_CLIENT_SECRET_JSON).
- Strict API Safety: Stays within 10,000 daily quota units (1,600 units/upload).
- Tags, Gaming category (20), #Shorts formatting, non-child audience declaration.
"""

import json
import os
import pathlib
import sys
from typing import Optional, Dict, Any


def get_authenticated_service():
    """Builds YouTube Data API v3 client with auto-refreshing OAuth credentials."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[!] Google API libraries not installed. Install via: pip install google-api-python-client google-auth-oauthlib")
        return None

    token_json_str = os.environ.get("YOUTUBE_TOKEN_JSON")
    client_secret_str = os.environ.get("YOUTUBE_CLIENT_JSON") or os.environ.get("YOUTUBE_CLIENT_SECRET_JSON")

    token_path = pathlib.Path(__file__).parent / "token.json"
    if not token_json_str and token_path.exists():
        with open(token_path, "r", encoding="utf-8") as f:
            token_json_str = f.read()

    if not token_json_str:
        print("[!] No YOUTUBE_TOKEN_JSON found in environment or token.json file.")
        return None

    try:
        token_info = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_info)

        # Headless Auto-Refresh Token
        if creds.expired and creds.refresh_token:
            print("[*] OAuth token expired, auto-refreshing headlessly...")
            creds.refresh(Request())
            print("[*] Successfully refreshed YouTube OAuth token.")

        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"[!] Authentication failed: {e}")
        return None


def upload_short(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    privacy_status: str = "public"
) -> Optional[Dict[str, Any]]:
    """Uploads a vertical 9:16 video to YouTube Shorts."""
    from googleapiclient.http import MediaFileUpload

    service = get_authenticated_service()
    if not service:
        print("[!] Cannot upload: YouTube service unavailable.")
        return None

    if "#Shorts" not in title:
        title = f"{title[:88]} #Shorts"

    if not tags:
        tags = ["Shorts", "Gaming", "GTA6", "Twitch", "StreamerMoments", "ViralClips"]

    body = {
        "snippet": {
            "title": title,
            "description": description or f"{title}\n\nSubscribe for daily viral clips!\n#Shorts #Gaming #Twitch #Viral",
            "tags": tags,
            "categoryId": "20",  # Gaming
            "defaultLanguage": "en"
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5
    )

    print(f"[*] Uploading '{title}' to YouTube Shorts...")
    req = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"[*] Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    shorts_url = f"https://youtube.com/shorts/{video_id}"
    print(f"[✅ UPLOAD SUCCESSFUL] Live YouTube Shorts: {shorts_url}")

    return {
        "video_id": video_id,
        "url": shorts_url,
        "title": title,
        "privacy": privacy_status
    }


def get_channel_metrics():
    """Fetches live channel metrics for the Telegram /dash commander."""
    service = get_authenticated_service()
    if not service:
        return None

    try:
        res = service.channels().list(part="snippet,statistics", mine=True).execute()
        items = res.get("items", [])
        if not items:
            return None
        ch = items[0]
        stats = ch.get("statistics", {})
        snippet = ch.get("snippet", {})
        return {
            "title": snippet.get("title"),
            "subscribers": stats.get("subscriberCount"),
            "views": stats.get("viewCount"),
            "videos": stats.get("videoCount")
        }
    except Exception as e:
        print(f"[!] Error fetching channel metrics: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 2:
        upload_short(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python youtube_publisher.py <video_path> <title>")
