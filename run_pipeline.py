#!/usr/bin/env python3
"""
Cooked Clips US - 100% Original Autonomous Shorts Runner
Generates original 14-18s high-retention Shorts (zero video clipping / zero Reused Content)
and publishes headlessly via YouTube Data API v3 on US GitHub Actions runners.
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

import editor
import youtube_publisher

# Curated high-retention curiosity & story bank (~14-16s spoken length for >100% APV loops)
TOPICS = [
    {
        "title": "Why Casinos Have Zero Clocks Or Windows 😱 #Shorts",
        "hook": "WHY CASINOS HIDE CLOCKS",
        "script": "Notice how Las Vegas casinos never have a single clock or window? They pump extra oxygen and use maze carpets so your brain completely loses track of time and keeps betting.",
        "wiki_slugs": ["Caesars_Palace", "Las_Vegas_Strip", "Slot_machine"],
        "tags": ["psychology", "lasvegas", "facts", "shorts", "didyouknow"],
    },
    {
        "title": "The $1 Million NASA Space Pen Lie 💀 #Shorts",
        "hook": "THE $1M SPACE PEN LIE",
        "script": "Everyone says NASA spent millions inventing a space pen while Russia used a pencil. Actually, graphite dust ruins electronics in zero gravity, and NASA bought normal Fisher pens for three dollars.",
        "wiki_slugs": ["Space_Pen", "Apollo_11", "International_Space_Station"],
        "tags": ["space", "nasa", "facts", "history", "shorts"],
    },
    {
        "title": "How 1 Tiny Key Mistake Sank The Titanic 🚢 #Shorts",
        "hook": "1 TINY KEY SANK TITANIC",
        "script": "The Titanic actually had binoculars onboard, locked inside a metal cabinet. A fired officer forgot to hand over the tiny key, leaving lookouts blind until the iceberg was right in front.",
        "wiki_slugs": ["Titanic", "Iceberg", "RMS_Titanic"],
        "tags": ["titanic", "history", "facts", "mystery", "shorts"],
    },
    {
        "title": "Why Supermarkets Put Milk At The Very Back 🥛 #Shorts",
        "hook": "THE SUPERMARKET TRAP",
        "script": "Supermarkets put milk and eggs in the furthest back corner on purpose. Forcing you to walk past twenty rows of snacks increases impulse spending by nearly forty percent every trip.",
        "wiki_slugs": ["Supermarket", "Grocery_store", "Shopping_cart"],
        "tags": ["psychology", "money", "facts", "tricks", "shorts"],
    },
    {
        "title": "The Hidden Trick Behind McDonald's Red And Yellow 🍔 #Shorts",
        "hook": "WHY FAST FOOD IS RED",
        "script": "McDonald's colors aren't random. Red naturally triggers urgency and hunger in your brain, while bright yellow grabs attention fast and pushes you to eat quickly and free up seats.",
        "wiki_slugs": ["McDonald%27s", "Hamburger", "French_fries"],
        "tags": ["business", "psychology", "facts", "shorts", "marketing"],
    },
    {
        "title": "Why An Octopus Has 3 Hearts And 9 Brains 🐙 #Shorts",
        "hook": "9 BRAINS IN 1 CREATURE",
        "script": "An octopus literally has nine brains and three hearts. Two hearts only pump blood to its gills, and the main third heart actually stops beating whenever it swims fast.",
        "wiki_slugs": ["Octopus", "Coral_reef", "Marine_biology"],
        "tags": ["ocean", "science", "animals", "facts", "shorts"],
    },
    {
        "title": "Why Airplane Windows Are Never Square ✈️ #Shorts",
        "hook": "WHY PLANE WINDOWS CURVE",
        "script": "The first jet airliners actually had square windows, and three planes broke apart mid-air. Sharp corners concentrate pressure, so engineers rounded every window to save millions of lives.",
        "wiki_slugs": ["De_Havilland_Comet", "Commercial_aircraft", "Jet_engine"],
        "tags": ["aviation", "engineering", "history", "facts", "shorts"],
    },
    {
        "title": "How Nintendo Started In 1889 (Not Video Games) 🃏 #Shorts",
        "hook": "NINTENDO'S SECRET ORIGIN",
        "script": "Nintendo isn't a modern tech company. It was founded in eighteen eighty-nine making handmade playing cards in Kyoto, nearly ninety years before Mario or video games even existed.",
        "wiki_slugs": ["Nintendo", "Hanafuda", "Super_Mario"],
        "tags": ["gaming", "nintendo", "history", "facts", "shorts"],
    },
    {
        "title": "Why You Never Hear Your Own Real Voice 🤯 #Shorts",
        "hook": "YOU HATE YOUR OWN VOICE",
        "script": "Your voice sounds deeper inside your head because your skull bones vibrate straight into your inner ear. What everyone else hears on recordings is actually how you sound.",
        "wiki_slugs": ["Human_voice", "Microphone", "Acoustic_wave"],
        "tags": ["psychology", "science", "facts", "brain", "shorts"],
    },
    {
        "title": "The Island Where Nobody Is Allowed To Die ❄️ #Shorts",
        "hook": "ILLEGAL TO DIE HERE",
        "script": "In Longyearbyen, Norway, dying is technically banned. Permafrost keeps buried bodies completely frozen for centuries, preserving ancient viruses, so critically ill residents must fly south.",
        "wiki_slugs": ["Longyearbyen", "Svalbard", "Permafrost"],
        "tags": ["geography", "weirdfacts", "travel", "shorts", "didyouknow"],
    },
    {
        "title": "Why Cleopatra Lived Closer To The iPhone Than Pyramids ⏳ #Shorts",
        "hook": "TIME WILL BREAK YOUR BRAIN",
        "script": "Cleopatra lived closer in time to the first iPhone launch than to the building of the Great Pyramid of Giza. When she ruled Egypt, the pyramids were already two thousand five hundred years old.",
        "wiki_slugs": ["Cleopatra", "Great_Pyramid_of_Giza", "IPhone"],
        "tags": ["history", "mindblown", "facts", "shorts", "didyouknow"],
    },
    {
        "title": "Why Rolex Is Actually A Non-Profit Charity ⌚ #Shorts",
        "hook": "ROLEX PAYS ALMOST ZERO TAX",
        "script": "When Rolex founder Hans Wilsdorf passed away with zero heirs, he left one hundred percent of the company to a private Swiss charity foundation, keeping Rolex profits largely tax-exempt.",
        "wiki_slugs": ["Rolex", "Switzerland", "Mechanical_watch"],
        "tags": ["money", "business", "luxury", "facts", "shorts"],
    },
]


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "6236827164")
    if not token:
        return
    try:
        payload = json.dumps({"chat_id": int(chat_id), "text": text, "parse_mode": "HTML"}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[!] Telegram alert note: {e}")


def build_topic_from_custom_query(query: str) -> dict:
    """Creates a clean Short script dynamically from Wikipedia for any topic requested via Telegram."""
    slug = query.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CookedClipsUS/2.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        title_clean = data.get("title", query)[:45]
        extract = data.get("extract", "")
        sentences = [s.strip() for s in extract.split(".") if len(s.strip()) > 15][:2]
        spoken = ". ".join(sentences) + "." if sentences else f"Here is the mind-blowing truth about {title_clean}."
        return {
            "title": f"The Truth About {title_clean} 🤯 #Shorts",
            "hook": title_clean.upper()[:28],
            "script": spoken[:260],
            "wiki_slugs": [slug, slug, slug],
            "tags": ["facts", "didyouknow", "history", "shorts", "mindblown"],
        }
    except Exception as e:
        print(f"[!] Custom topic lookup fallback ({e}), using curated slot.")
        return TOPICS[0]


def pick_slot_topic(custom_topic: str = "") -> dict:
    if custom_topic and custom_topic.strip():
        return build_topic_from_custom_query(custom_topic)
    now = datetime.datetime.now(datetime.timezone.utc)
    day_num = now.timetuple().tm_yday
    slot_idx = 0 if now.hour < 21 else 1
    idx = (day_num * 2 + slot_idx) % len(TOPICS)
    return TOPICS[idx]


def run_slot(custom_topic: str = "") -> bool:
    topic = pick_slot_topic(custom_topic)
    session_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    work_dir = pathlib.Path("output") / f"job_{session_id}"
    out_video = pathlib.Path("output") / f"short_{session_id}.mp4"

    print(f"[*] Generating 100% Original Short: {topic['title']}")
    ok, dur = editor.render_original_short(topic, str(out_video), work_dir)
    if not ok:
        send_telegram("❌ <b>Cloud Render Failed</b> — FFmpeg error in GitHub Actions.")
        return False

    integrity = editor.verify_video_integrity(str(out_video))
    print(f"[*] Integrity check: {integrity}")
    if not integrity.get("valid"):
        send_telegram(f"❌ <b>Integrity Check Failed:</b> <code>{integrity.get('error')}</code>")
        return False

    desc = (
        f"{topic['title']}\n\n"
        "Did you already know this, or were you surprised? Comment below 👇\n\n"
        "Subscribe for 2 mind-blowing stories every day!\n#Shorts #Facts #DidYouKnow"
    )
    yt_res = youtube_publisher.upload_short(
        video_path=str(out_video),
        title=topic["title"],
        description=desc,
        tags=topic["tags"],
        privacy_status="public",
        category_id="27",  # Education
    )
    if yt_res and yt_res.get("url"):
        send_telegram(
            f"🚀 <b>NEW ORIGINAL SHORT PUBLISHED</b>\n\n"
            f"🎬 <b>Title:</b> {topic['title']}\n"
            f"⏱️ <b>Length:</b> {integrity['duration']}s (9:16 HD)\n"
            f"▶️ <b>YouTube:</b> {yt_res['url']}"
        )
        return True

    send_telegram("❌ <b>YouTube Upload Failed</b> — Check <code>YOUTUBE_TOKEN_JSON</code> secret.")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cooked Clips US Original Shorts Runner")
    parser.add_argument("--topic", default="", help="Optional custom Wikipedia/fact topic")
    args = parser.parse_args()
    if not run_slot(args.topic):
        sys.exit(1)
