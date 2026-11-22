#!/usr/bin/env python3
"""
Cooking Clip US - Meta Long-Lived Token Exchange
Exchanges a temporary 1-hour Meta token for a permanent 60-day token.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import sys


def exchange_token(app_id: str, app_secret: str, short_lived_token: str):
    print("\n[*] Exchanging temporary token for 60-day long-lived token...")
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token
    }
    url = f"https://graph.facebook.com/v20.0/oauth/access_token?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            long_token = data.get("access_token")
            expires_in = data.get("expires_in", 5184000)
            days = expires_in // 86400
            print(f"\n[✅ SUCCESS!] Generated 60-Day Long-Lived Token (Valid for {days} days)")
            print(f"\nSave this as INSTAGRAM_ACCESS_TOKEN in GitHub Secrets:\n\n{long_token}\n")
            return long_token
    except urllib.error.HTTPError as e:
        print(f"[!] Token exchange error: {e.read().decode()}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 3:
        exchange_token(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python token_exchange.py <app_id> <app_secret> <short_lived_token>")
