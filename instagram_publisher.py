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


def upload_reel_meta_resumable(
    video_path: str,
    caption: str,
    access_token: Optional[str] = None,
    account_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Uploads local video directly to Instagram Reels via Meta Graph API resumable upload."""
    import requests
    import subprocess

    token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    ig_id = account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID")

    if not token or not ig_id:
        return None

    # Pre-process video with ffmpeg for Instagram specifications if needed
    proc_path = video_path
    if os.path.exists(video_path):
        norm_path = video_path.replace(".mp4", "_ig_norm.mp4")
        norm_cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-movflags", "+faststart", norm_path
        ]
        try:
            p = subprocess.run(norm_cmd, capture_output=True, text=True)
            if p.returncode == 0 and os.path.exists(norm_path):
                proc_path = norm_path
        except Exception:
            pass

    file_size = os.path.getsize(proc_path)
    api_base = "https://graph.facebook.com/v20.0"

    try:
        # Step 1: Init container
        init_res = requests.post(f"{api_base}/{ig_id}/media", data={
            "access_token": token,
            "upload_type": "resumable",
            "media_type": "REELS",
            "caption": caption,
            "share_to_feed": "true"
        }).json()

        container_id = init_res.get("id")
        upload_uri = init_res.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v20.0/{container_id}"

        # Step 2: Upload binary
        with open(proc_path, "rb") as f:
            up_res = requests.post(
                upload_uri,
                headers={
                    "Authorization": f"OAuth {token}",
                    "offset": "0",
                    "file_size": str(file_size),
                    "Content-Type": "application/octet-stream"
                },
                data=f
            )

        # Clean up temporary normalized file
        if proc_path != video_path and os.path.exists(proc_path):
            try:
                os.remove(proc_path)
            except Exception:
                pass

        if up_res.status_code != 200:
            print(f"[!] Binary upload failed: {up_res.text}")
            return None

        # Step 3: Poll status
        for _ in range(40):
            time.sleep(5)
            st_data = requests.get(f"{api_base}/{container_id}", params={"access_token": token, "fields": "status_code"}).json()
            if st_data.get("status_code") == "FINISHED":
                break
            elif st_data.get("status_code") == "ERROR":
                print(f"[!] Reel processing error: {st_data}")
                return None

        # Step 4: Publish
        pub_res = requests.post(f"{api_base}/{ig_id}/media_publish", data={"access_token": token, "creation_id": container_id}).json()
        post_id = pub_res.get("id")
        if not post_id:
            return None

        info = requests.get(f"{api_base}/{post_id}", params={"access_token": token, "fields": "permalink"}).json()
        reel_url = info.get("permalink", f"https://www.instagram.com/reel/{post_id}/")
        print(f"[🚀 REEL PUBLISHED!] Live URL: {reel_url}")
        return {"id": post_id, "url": reel_url, "status": "PUBLISHED"}
    except Exception as e:
        print(f"[!] Meta Resumable API Error: {e}")
        return None


def upload_reel(video_path: str, caption: str, video_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Master uploader: Tries Direct 2-Env-Var login first, then Meta API."""
    # 1. Try Direct 2 Env Vars (Username + Password)
    if os.environ.get("INSTAGRAM_PASSWORD"):
        res = upload_reel_direct(video_path, caption)
        if res:
            return res

    # 2. Try Meta API (Local Resumable Upload)
    if os.environ.get("INSTAGRAM_ACCESS_TOKEN") and os.path.exists(video_path):
        res = upload_reel_meta_resumable(video_path, caption)
        if res:
            return res

    # 3. Try Meta API (URL-based Upload)
    if os.environ.get("INSTAGRAM_ACCESS_TOKEN") and (video_url or video_path.startswith("http")):
        return upload_reel_meta_api(video_url or video_path, caption)

    print("[*] No active Instagram publishing credentials found. Staging video locally.")
    return None


if __name__ == "__main__":
    if len(sys.argv) > 2:
        upload_reel(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python instagram_publisher.py <video_path> <caption>")
