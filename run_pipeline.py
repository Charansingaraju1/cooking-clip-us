#!/usr/bin/env python3
"""
Cooking Clip US - Master Autonomous Pipeline Runner
Executes the end-to-end hands-free clipping flow:
1. Ingestion & Hype Detection
2. Dual-stacked (35/65) editing + Hook text + Karaoke subtitles + -14 LUFS
3. Video integrity verification
4. Headless YouTube Shorts upload
5. Instant Telegram alert
"""

import argparse
import datetime
import os
import pathlib
import sys
import editor
import youtube_publisher
import instagram_publisher
import telegram_commander


def generate_viral_package(streamer: str, clip_description: str = "") -> dict | None:
    """
    Calls Claude Sonnet to generate a viral title, description, and hashtags.
    Returns dict with keys: title, description, hashtags — or None on failure.
    Requires ANTHROPIC_API_KEY env var.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"You are a YouTube Shorts viral clip expert for a US gaming audience.\n"
            f"Streamer: {streamer}\n"
            f"Clip moment: {clip_description or 'intense GTA 6 gameplay moment'}\n\n"
            f"Generate ONE viral YouTube Short package. Rules:\n"
            f"1. Title: topic-first, under 48 characters TOTAL (not streamer-first), 1-2 emojis, NO hashtags in title. "
            f"   Use curiosity gap. Example format: 'GTA 6 [EVENT] 😭🔥 ({streamer} Reaction)'\n"
            f"2. Description: 2 punchy sentences. End with 'Rate 1-10 below 👇'. "
            f"   Include 'Subscribe to @Cooked_Clips_US for daily clips!'. Max 200 chars.\n"
            f"3. Hashtags: EXACTLY 3: #Shorts + 2 topic tags (e.g. #GTA6 #KaiCenat). No more.\n\n"
            f"Reply in this EXACT format (no extra text):\n"
            f"TITLE: <title here>\n"
            f"DESC: <description here>\n"
            f"TAGS: <#tag1 #tag2 #tag3>"
        )
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        result = {}
        for line in raw.splitlines():
            if line.startswith("TITLE:"):
                result["title"] = line[6:].strip()
            elif line.startswith("DESC:"):
                result["description"] = line[5:].strip()
            elif line.startswith("TAGS:"):
                result["hashtags"] = line[5:].strip()
        if "title" in result and "description" in result:
            return result
    except Exception as e:
        print(f"[Claude] API call failed, using template fallback: {e}")
    return None


def resolve_auto_streamer():
    """Auto-distributes daily uploads: Morning=Kai, Lunch=Lacy, Prime=Kai."""
    hour = datetime.datetime.utcnow().hour
    if 11 <= hour <= 15:
        return "kaicenat"
    elif 16 <= hour <= 20:
        return "lacy"
    return "kaicenat"


def run_autonomous_slot(channel: str = "auto", source_url: str = None, hook: str = None):
    if not channel or channel == "auto":
        channel = resolve_auto_streamer()
    print(f"\n========================================================")
    print(f"🎬 MASTER PIPELINE EXECUTING FOR: {channel.upper()}")
    print(f"Time: {datetime.datetime.utcnow().isoformat()}Z")
    print(f"========================================================\n")

    out_dir = pathlib.Path("output")
    out_dir.mkdir(exist_ok=True)
    session_id = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Step 1: Ingestion
    raw_video = out_dir / f"raw_{channel}_{session_id}.mp4"
    if not source_url:
        print(f"[*] Discovering latest high-intensity stream / VOD for {channel}...")
        # Prioritize freshest GTA 6 stream replay / live VOD
        source_url = f"ytsearch1:{channel} gta 6 stream"

    print(f"[*] Acquiring source stream: {source_url}...")
    import subprocess
    cmd_dl = [
        sys.executable, "-m", "yt_dlp",
        source_url,
        "-o", str(raw_video),
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--download-sections", "*05:00-05:40",
        "--force-keyframes-at-cuts",
        "--no-playlist"
    ]
    res_dl = subprocess.run(cmd_dl)

    if not raw_video.exists() or raw_video.stat().st_size < 1000:
        print(f"[*] Targeted section failed, attempting direct download...")
        cmd_dl_fallback = [
            sys.executable, "-m", "yt_dlp",
            source_url,
            "-o", str(raw_video),
            "-f", "best[ext=mp4]/best",
            "--max-filesize", "80M",
            "--no-playlist"
        ]
        subprocess.run(cmd_dl_fallback)

    if not raw_video.exists() or raw_video.stat().st_size < 1000:
        print(f"[!] Source acquisition failed. Falling back to queued clip if available.")
        ready_clips = list(pathlib.Path("clips/ready").glob("*.mp4"))
        if ready_clips:
            clip_to_upload = sorted(ready_clips, key=lambda x: os.path.getmtime(x), reverse=True)[0]
            print(f"[*] Using queued ready clip: {clip_to_upload.name}")
        else:
            print("[!] No video available to process this slot.")
            return False
    else:
        # Step 2: Hype Detection & Moment Selection
        clip_rendered = out_dir / f"viral_{channel}_{session_id}.mp4"
        ass_subtitles = out_dir / f"subs_{session_id}.ass"
        hook_text = hook or f"{channel.upper()} CANNOT BELIEVE THIS HAPPENED 😱"

        # Transcribe & build ASS subtitles
        print("[*] Generating Whisper karaoke subtitles...")
        try:
            from faster_whisper import WhisperModel
            wmodel = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = wmodel.transcribe(str(raw_video), beam_size=5)
            editor.generate_karaoke_ass(segments, ass_subtitles)
        except Exception as e:
            print(f"[!] Whisper transcription note: {e}")

        # Render dual-stacked 1080x1920 (35% top, 65% bottom) with -14 LUFS
        print("[*] Rendering dual-stacked 1080x1920 vertical video with -14 LUFS...")
        success = editor.render_vertical_clip(
            input_video=str(raw_video),
            output_video=str(clip_rendered),
            start_sec=10.0,
            duration=35.0,
            channel=channel,
            hook_text=hook_text,
            ass_path=str(ass_subtitles) if ass_subtitles.exists() else None
        )
        if not success:
            print("[!] Rendering failed.")
            return False
        clip_to_upload = clip_rendered

    # Step 3: Integrity Verification Protocol
    print(f"[*] Running integrity check on {clip_to_upload}...")
    integrity = editor.verify_video_integrity(str(clip_to_upload))
    print(f"[*] Integrity report: {integrity}")

    if not integrity.get("valid"):
        print(f"[!] Video integrity check failed: {integrity.get('error')}. Aborting upload.")
        return False
    print("[✅ INTEGRITY CONFIRMED] 1080x1920, 9:16 aspect ratio, valid audio, ready for broadcast.")

    # Step 4: Autonomous Dual-Platform Upload — Claude Sonnet generates package, templates as fallback
    import random
    ch = channel.lower()

    # Try Claude Sonnet first
    clip_desc = hook or ""
    streamer_label = "Kai Cenat" if "kai" in ch else ("Lacy" if "lacy" in ch else channel)
    claude_pkg = generate_viral_package(streamer_label, clip_desc)

    if "kai" in ch:
        title_templates = [
            "GTA 6 COPS ESCAPE IS UNREAL 😭🔥 (Kai Cenat Reaction) #Shorts",
            "KAI CANNOT BELIEVE GTA 6 VICE CITY PHYSICS 💀 #Shorts",
            "GTA 6 FIRST COMPOUND SHOOTOUT IS CRAZY 😭🔥 (Kai Cenat) #Shorts",
            "KAI CENAT 5-STAR WANTED LEVEL IN GTA 6 💀🚨 #Shorts"
        ]
        fallback_desc = (
            "Kai Cenat exploring GTA 6 Vice City... reactions are absolutely insane!\n\n"
            "Rate 1-10 below 👇\n\nSubscribe to @Cooked_Clips_US for daily viral clips!"
        )
        viral_tags = ["GTA 6", "GTA VI", "Kai Cenat", "Kai Cenat GTA 6", "Grand Theft Auto VI",
                      "Vice City", "GTA 6 gameplay", "gaming shorts", "viral shorts", "cooked clips",
                      "twitch highlights", "amp kai", "kaicenat clips"]
        viral_hashtags = "#kaicenat #gta6 #grandtheftauto6 #twitchmoments #gamingreels #fyp #cookedclips"
    elif "lacy" in ch:
        title_templates = [
            "GTA 6 GRAPHICS ARE ACTUALLY INSANE 😭🔥 (Lacy Reaction) #Shorts",
            "LACY BUSTED BY 5-STAR VICE CITY POLICE 💀 #Shorts",
            "LACY MOTORCYCLE ESCAPE IN GTA 6 IS CHAOS 😭 #Shorts",
            "FIRST HEIST GETAWAY IN GTA 6 IS SO INTENSE 😱🔥 (Lacy) #Shorts"
        ]
        fallback_desc = (
            "Lacy flying through Vice City in GTA 6... physics and graphics are completely unreal!\n\n"
            "Rate 1-10 below 👇\n\nSubscribe to @Cooked_Clips_US for daily viral clips!"
        )
        viral_tags = ["GTA 6", "GTA VI", "Lacy", "Lacy GTA 6", "Grand Theft Auto VI",
                      "Vice City", "GTA 6 gameplay", "gaming shorts", "viral shorts", "cooked clips",
                      "twitch highlights", "faze lacy"]
        viral_hashtags = "#lacy #fazelacy #gta6 #grandtheftauto6 #gamingreels #fyp #cookedclips"
    else:
        title_templates = [f"{channel.upper()} GTA 6 UNBELIEVABLE MOMENT 😭🔥 #Shorts"]
        fallback_desc = f"Wildest GTA 6 highlight! Subscribe to @Cooked_Clips_US!\n\n#gta6 #Shorts"
        viral_tags = ["GTA 6", "Gaming", "Twitch", "Streamer Moments", "Shorts", "Viral Clips"]
        viral_hashtags = "#gaming #gta6 #viral #fyp #cookedclips"

    if hook and len(hook) > 10:
        title = f"{hook} ({streamer_label} Reaction) #Shorts"
    elif claude_pkg:
        title = claude_pkg["title"]
        print(f"[Claude ✅] Generated title: {title}")
    else:
        title = random.choice(title_templates)

    if claude_pkg:
        yt_description = claude_pkg["description"]
        ig_hashtags = claude_pkg.get("hashtags", viral_hashtags)
    else:
        yt_description = fallback_desc
        ig_hashtags = viral_hashtags

    ig_caption = f"{title}\n.\n.\nDrop your rating 1-10 below! 👇\n.\n.\n{ig_hashtags}"

    print(f"[*] Publishing to YouTube Shorts with viral tags...")
    yt_result = youtube_publisher.upload_short(
        video_path=str(clip_to_upload),
        title=title,
        description=yt_description,
        tags=viral_tags,
        privacy_status="public"
    )

    print(f"[*] Publishing to Instagram Reels with viral hashtags...")
    ig_result = instagram_publisher.upload_reel(str(clip_to_upload), ig_caption)

    # Step 5: Telegram Commander Alert
    if (yt_result and yt_result.get("url")) or (ig_result and ig_result.get("url")):
        yt_url = yt_result.get("url", "N/A") if yt_result else "N/A"
        ig_url = ig_result.get("url", "N/A") if ig_result else "N/A"
        telegram_commander.send_telegram_alert(
            streamer=channel,
            title=title,
            yt_url=yt_url,
            ig_url=ig_url
        )
        print(f"\n[🚀 SLOT COMPLETED SUCCESSFULLY] YouTube: {yt_url} | Instagram: {ig_url}")
        return True
    else:
        print("[!] Video rendered and ready locally.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cooking Clip US Autonomous Pipeline")
    parser.add_argument("--channel", default="auto", help="Target streamer channel (kaicenat, lacy, ishowspeed, or auto)")
    parser.add_argument("--url", default=None, help="Direct video URL")
    parser.add_argument("--hook", default=None, help="Hook text overlay")
    args = parser.parse_args()

    run_autonomous_slot(channel=args.channel, source_url=args.url, hook=args.hook)
