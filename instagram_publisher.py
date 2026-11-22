#!/usr/bin/env python3
"""
Cooking Clip US - Headless Instagram Reels Publisher
Publishes vertical 9:16 video to Instagram Reels via official Meta Graph API.
Features:
- Headless execution (uses INSTAGRAM_ACCESS_TOKEN & INSTAGRAM_ACCOUNT_ID).
- Automatic container status polling until ready before media_publish.
- Attaches viral caption, #reels hashtags, and share_to_feed flag.
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


def upload_reel(
    video_url: str,
    caption: str,
    access_token: Optional[str] = None,
    account_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Publishes a vertical 9:16 clip to Instagram Reels via Meta Graph API."""
    token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    ig_id = account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID")

    if not token or not ig_id:
        print("[*] Instagram credentials (INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID) not found. Skipping Instagram publish.")
        return None

    api_base = "https://graph.facebook.com/v20.0"
    print(f"[*] Initializing Instagram Reels container for account {ig_id}...")

    # Step 1: Create Container
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
            res_data = json.loads(resp.read().decode())
            creation_id = res_data.get("id")

        if not creation_id:
            print("[!] Failed to get container creation_id from Instagram.")
            return None

        print(f"[*] Container created (ID: {creation_id}). Polling processing status...")

        # Step 2: Poll container status until FINISHED
        status_url = f"{api_base}/{creation_id}?fields=status_code&access_token={token}"
        for _ in range(30):
            time.sleep(5)
            with urllib.request.urlopen(status_url) as s_resp:
                s_data = json.loads(s_resp.read().decode())
                status_code = s_data.get("status_code")
                print(f"[*] Container status: {status_code}")
                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    print("[!] Instagram video processing failed.")
                    return None

        # Step 3: Publish Container
        pub_url = f"{api_base}/{ig_id}/media_publish"
        pub_payload = {
            "creation_id": creation_id,
            "access_token": token
        }
        pub_data = urllib.parse.urlencode(pub_payload).encode("utf-8")
        pub_req = urllib.request.Request(pub_url, data=pub_data)
        with urllib.request.urlopen(pub_req) as p_resp:
            publish_res = json.loads(p_resp.read().decode())
            post_id = publish_res.get("id")

        reels_url = f"https://www.instagram.com/reel/{post_id}/"
        print(f"[✅ INSTAGRAM REELS PUBLISHED] Live Reel: {reels_url}")
        return {
            "post_id": post_id,
            "url": reels_url,
            "status": "PUBLISHED"
        }

    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[!] Instagram Graph API Error ({e.code}): {err}")
        return None
    except Exception as e:
        print(f"[!] Unexpected error publishing to Instagram: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        upload_reel(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python instagram_publisher.py <video_url> <caption>")
