#!/usr/bin/env python3
"""
Cooking Clip US - Instagram Connection Helper
Tests connection to @cooked_clips_us and outputs GitHub Secret values.
"""

import json
import os
import sys
import urllib.request
import urllib.error


def test_meta_graph_api(access_token: str, account_id: str):
    """Verifies access token and Instagram account permissions."""
    print("\n[*] Testing Meta Graph API credentials...")
    url = f"https://graph.facebook.com/v20.0/{account_id}?fields=username,name,profile_picture_url&access_token={access_token}"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            print(f"\n[✅ CONNECTION SUCCESSFUL!]")
            print(f"Connected to Instagram Account: @{data.get('username')}")
            print(f"Account Name: {data.get('name')}")
            print("\nAdd these two secrets to GitHub (Repo Settings > Secrets > Actions):")
            print(f"1. INSTAGRAM_ACCESS_TOKEN: {access_token[:10]}... (your token)")
            print(f"2. INSTAGRAM_ACCOUNT_ID: {account_id}")
            return True
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"\n[!] Connection Failed ({e.code}): {err}")
        return False


if __name__ == "__main__":
    print("==================================================")
    print(" 🎬 CONNECT INSTAGRAM TO COOKING CLIP US PIPELINE")
    print("==================================================")
    token = input("\nEnter your Meta Graph API Access Token: ").strip()
    acct_id = input("Enter your Instagram Business Account ID: ").strip()

    if token and acct_id:
        test_meta_graph_api(token, acct_id)
    else:
        print("[!] Token or Account ID missing.")
