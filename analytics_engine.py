#!/usr/bin/env python3
"""
Cooking Clip US - Live YouTube Shorts Performance Monitor
Dynamically scans public channel uploads on @Cooked_Clips_US and audits view velocity.
"""

import datetime
import json
import re
import urllib.request
from typing import Dict, Any, List


def discover_channel_shorts(channel_handle: str = "@Cooked_Clips_US", limit: int = 15) -> List[str]:
    """Pulls latest Short video IDs directly from the public YouTube channel page."""
    url = f"https://www.youtube.com/{channel_handle}/shorts"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        ids = list(dict.fromkeys(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)))
        return ids[:limit]
    except Exception:
        return ["aOQsf2H7flw", "lxBks72Ku4s", "89TyL4qEXpc"]


def fetch_video_stats(video_id: str) -> Dict[str, Any]:
    res = {"id": video_id, "url": f"https://youtube.com/shorts/{video_id}", "title": video_id, "views": 0}
    try:
        oembed = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(urllib.request.Request(oembed, headers={"User-Agent": "Mozilla/5.0"}), timeout=5) as r:
            res["title"] = json.loads(r.read().decode("utf-8")).get("title", video_id)
    except Exception:
        pass
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://www.youtube.com/watch?v={video_id}", headers={"User-Agent": "Mozilla/5.0"}), timeout=5) as r:
            html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r'"viewCount":"(\d+)"', html)
            if m:
                res["views"] = int(m.group(1))
    except Exception:
        pass
    return res


def run_performance_audit() -> Dict[str, Any]:
    ids = discover_channel_shorts()
    clips = [fetch_video_stats(vid) for vid in ids]
    total_views = sum(c["views"] for c in clips)
    top = max(clips, key=lambda x: x["views"]) if clips else None
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "channel": "@Cooked_Clips_US",
        "total_tracked_clips": len(clips),
        "total_views": total_views,
        "average_views_per_clip": round(total_views / len(clips), 1) if clips else 0,
        "top_performing_clip": top,
        "clips": clips,
    }


if __name__ == "__main__":
    audit = run_performance_audit()
    top = audit["top_performing_clip"] or {}
    print(f"[+] Channel: {audit['channel']} | Shorts: {audit['total_tracked_clips']} | Total Views: {audit['total_views']:,} | Avg: {audit['average_views_per_clip']}")
    print(f"[+] Top Short: {top.get('title')} ({top.get('views', 0):,} views)")
