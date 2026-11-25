#!/usr/bin/env python3
"""
Cooked Clips US - 100% Original High-Retention Shorts Generator
Zero third-party video clipping. Synthesizes HD Wikipedia visuals with smooth zoom,
Edge-TTS WordBoundary synced captions, top hook banner, countdown bar, and -20dB BGM.
"""

import asyncio
import json
import os
import pathlib
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance

VOICE_NAME = "en-US-AndrewNeural"


def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _prepare_scene_image(src_img: Optional[Image.Image], dest_jpg: pathlib.Path, idx: int) -> str:
    """Normalizes image to 1200x2134 (9:16 oversampled for smooth zoom) with dark vignette."""
    W, H = 1200, 2134
    if src_img is None:
        # Procedural dark gradient fallback if external image fetch fails.
        palettes = [((18, 28, 48), (6, 10, 18)), ((40, 18, 32), (10, 6, 14)), ((16, 42, 38), (6, 12, 12))]
        c_top, c_bot = palettes[idx % len(palettes)]
        canvas = Image.new("RGB", (W, H), c_bot)
        draw = ImageDraw.Draw(canvas)
        for y in range(0, H, 8):
            t = y / H
            r = int(c_top[0] * (1 - t) + c_bot[0] * t)
            g = int(c_top[1] * (1 - t) + c_bot[1] * t)
            b = int(c_top[2] * (1 - t) + c_bot[2] * t)
            draw.rectangle([(0, y), (W, y + 8)], fill=(r, g, b))
    else:
        img = src_img.convert("RGB")
        iw, ih = img.size
        target_ratio = W / H
        if iw / ih > target_ratio:
            new_w = int(ih * target_ratio)
            left = (iw - new_w) // 2
            img = img.crop((left, 0, left + new_w, ih))
        else:
            new_h = int(iw / target_ratio)
            top = (ih - new_h) // 2
            img = img.crop((0, top, iw, top + new_h))
        canvas = img.resize((W, H), Image.Resampling.LANCZOS)
        canvas = ImageEnhance.Color(canvas).enhance(1.15)
        canvas = ImageEnhance.Contrast(canvas).enhance(1.08)

    # Top and bottom dark vignette so white/yellow overlays read effortlessly.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(0, 420, 4):
        alpha = int(190 * (1 - y / 420))
        odraw.rectangle([(0, y), (W, y + 4)], fill=(0, 0, 0, alpha))
    for y in range(H - 650, H, 4):
        alpha = int(210 * ((y - (H - 650)) / 650))
        odraw.rectangle([(0, y), (W, y + 4)], fill=(0, 0, 0, alpha))

    merged = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    dest_jpg.parent.mkdir(parents=True, exist_ok=True)
    merged.save(dest_jpg, quality=92)
    return str(dest_jpg.resolve())


def fetch_wikipedia_scene(wiki_slug: str, dest_jpg: pathlib.Path, idx: int) -> str:
    """Downloads a crisp CC/public-domain visual from Wikipedia's REST Summary API."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_slug)}"
    headers = {"User-Agent": "CookedClipsUS/2.0 (https://github.com/Charansingaraju1/cooking-clip-us)"}
    img_obj = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        img_url = (data.get("originalimage") or data.get("thumbnail") or {}).get("source")
        if img_url:
            ireq = urllib.request.Request(img_url, headers=headers)
            img_path = dest_jpg.with_suffix(".raw")
            with urllib.request.urlopen(ireq, timeout=12) as iresp:
                img_path.write_bytes(iresp.read())
            img_obj = Image.open(img_path)
            img_obj.load()
            img_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"[!] Visual fetch fallback for {wiki_slug}: {e}")
    return _prepare_scene_image(img_obj, dest_jpg, idx)


def synthesize_tts_with_sync(
    script_text: str,
    mp3_path: pathlib.Path,
    ass_path: pathlib.Path,
    hook_banner: str,
) -> float:
    """Synthesizes Edge-TTS voiceover and writes exact WordBoundary 2-3 word ASS captions."""
    words: List[Tuple[float, float, str]] = []

    async def _run():
        comm = edge_tts.Communicate(script_text, VOICE_NAME, rate="+14%", boundary="WordBoundary")
        audio_bytes = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_s = chunk["offset"] / 1e7
                dur_s = max(chunk["duration"] / 1e7, 0.12)
                words.append((start_s, start_s + dur_s, chunk["text"]))
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        mp3_path.write_bytes(bytes(audio_bytes))

    import edge_tts
    asyncio.run(_run())

    # Group into snappy 2-3 word chunks for effortless mobile reading.
    events = []
    clean_hook = re.sub(r"[^\w\s.,!?'\"$%-]", "", hook_banner or "").strip().upper()
    if clean_hook:
        events.append(f"Dialogue: 1,0:00:00.00,0:00:04.00,TopHook,,0,0,0,,{clean_hook}")

    i = 0
    while i < len(words):
        chunk = words[i : i + 3]
        c_start = chunk[0][0]
        c_end = words[i + 3][0] if i + 3 < len(words) else chunk[-1][1] + 0.20
        phrase = " ".join(w[2] for w in chunk).upper().replace("{", "").replace("}", "")
        events.append(
            f"Dialogue: 0,{format_ass_time(c_start)},{format_ass_time(c_end)},CaptionMain,,0,0,0,,{phrase}"
        )
        i += 3

    header = """[Script Info]
Title: Cooked Clips US Original Shorts
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CaptionMain,DejaVu Sans,78,&H0000FFFF,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,420,1
Style: TopHook,DejaVu Sans,62,&H00FFFFFF,&H000000FF,&H000000FF,&HE01414D8,-1,0,0,0,100,100,0,0,3,18,0,8,60,60,130,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

    last_end = words[-1][1] if words else 12.0
    return max(round(last_end + 0.40, 2), 11.0)


def render_original_short(
    topic: Dict[str, object],
    output_video: str,
    work_dir: pathlib.Path,
) -> Tuple[bool, float]:
    """Builds a complete 1080x1920 30fps vertical Short with scenes, motion, sync captions, and BGM."""
    work_dir.mkdir(parents=True, exist_ok=True)
    out_p = pathlib.Path(output_video).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    mp3_path = (work_dir / "narration.mp3").resolve()
    ass_path = (work_dir / "subs.ass").resolve()

    total_dur = synthesize_tts_with_sync(
        script_text=str(topic["script"]),
        mp3_path=mp3_path,
        ass_path=ass_path,
        hook_banner=str(topic["hook"]),
    )

    slugs = list(topic.get("wiki_slugs") or ["Earth", "Moon", "Sun"])
    while len(slugs) < 3:
        slugs.append(slugs[-1])

    scene_files = [
        fetch_wikipedia_scene(slugs[i], work_dir / f"scene_{i}.jpg", i)
        for i in range(3)
    ]

    seg_dur = total_dur / 3.0
    seg_frames = max(int(round(seg_dur * 30)), 30)

    bgm_candidates = [
        pathlib.Path("assets/viral_bgm.mp3").resolve(),
        pathlib.Path(__file__).parent.resolve() / "assets" / "viral_bgm.mp3",
    ]
    bgm_file = next((p for p in bgm_candidates if p.exists()), None)

    # Inputs: 0..2 = 3 scene images (single frame each -> zoompan expands to seg_frames cleanly), 3 = narration MP3, optional 4 = viral BGM
    cmd = ["ffmpeg", "-y"]
    for sf in scene_files:
        cmd += ["-i", sf]
    cmd += ["-i", str(mp3_path)]
    if bgm_file:
        cmd += ["-i", str(bgm_file)]

    # Smooth Ken Burns zoom-in per scene + animated red progress bar + bold ASS captions
    v_filters = []
    for i in range(3):
        v_filters.append(
            f"[{i}:v]scale=1200:2134,zoompan=z='min(zoom+0.0012,1.12)':d={seg_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1[v{i}]"
        )
    v_filters.append("[v0][v1][v2]concat=n=3:v=1:a=0[vcat]")
    v_filters.append(f"color=c=0xFF204E:s=1080x14:r=30:d={total_dur:.2f}[bar]")
    v_filters.append(f"[vcat][bar]overlay=x='-W+(t/{total_dur:.2f})*W':y=0:shortest=1[vbar]")
    v_filters.append(f"[vbar]ass={ass_path.name}[vout]")

    if bgm_file:
        a_filter = (
            "[4:a]aloop=loop=-1:size=2e+09,volume=0.10[bgm];"
            "[3:a]apad,volume=1.35[vo];"
            "[vo][bgm]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=7:tp=-1.5[aout]"
        )
    else:
        a_filter = "[3:a]apad,volume=1.35,loudnorm=I=-14:LRA=7:tp=-1.5[aout]"

    filter_complex = ";".join(v_filters) + ";" + a_filter

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-t", f"{total_dur:.2f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(out_p),
    ]

    res = subprocess.run(cmd, cwd=str(work_dir), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] FFmpeg error: {res.stderr[-500:]}")
        return False, 0.0
    return True, total_dur


def verify_video_integrity(video_path: str) -> dict:
    """Verifies resolution, duration, and audio/video streams using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        return {"valid": False, "error": "ffprobe failed"}

    try:
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not v_stream or not a_stream:
            return {"valid": False, "error": "Missing video or audio stream"}

        w = int(v_stream.get("width", 0))
        h = int(v_stream.get("height", 0))
        dur = float(data.get("format", {}).get("duration", 0.0))
        valid = (w == 1080 and h == 1920 and 10.0 <= dur <= 45.0)
        return {
            "valid": valid,
            "width": w,
            "height": h,
            "duration": round(dur, 2),
            "aspect_ratio": f"{w}x{h} (9:16)",
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
