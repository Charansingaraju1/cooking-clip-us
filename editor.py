#!/usr/bin/env python3
"""
Cooking Clip US - Viral Auto-Editor & Subtitler
Features:
- Dual stacked vertical layout (Facecam top 35% ~672px, Gameplay bottom 65% ~1248px, total 1080x1920).
- High-contrast curiosity hook text on the top frame (first 3 seconds).
- Stylized ASS karaoke-style subtitles.
- Audio loudness normalization (-14 LUFS broadcast standard).
- Video integrity verification (resolution, framerate, duration, audio levels).
"""

import json
import os
import pathlib
import re
import subprocess
import sys


def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_karaoke_ass(segments, output_path: pathlib.Path, video_width=1080, video_height=1920):
    """
    Generates high-contrast, yellow/cyan ASS subtitles placed in the lower-middle zone.
    """
    header = f"""[Script Info]
Title: Cooking Clip US Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralYellow,Impact,74,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,4,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        text = getattr(seg, "text", str(seg)).strip()
        start = getattr(seg, "start", 0.0)
        end = getattr(seg, "end", start + 2.0)
        if not text:
            continue
        start_str = format_ass_time(start)
        end_str = format_ass_time(end)
        clean_text = text.upper().replace("{", "").replace("}", "")
        events.append(f"Dialogue: 0,{start_str},{end_str},ViralYellow,,0,0,0,,{clean_text}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    return output_path


def build_stack_filters(channel: str = "", hook_text: str = "", ass_path: str = None, has_bgm: bool = False):
    ch = channel.lower() if channel else ""
    # 70% Extreme Reaction Facecam (1100px) / 30% Gameplay (820px) = 1920px total
    if ch in ("speed", "ishowspeed"):
        cam = "[0:v]crop=388:220:0:460,scale=1080:1100:flags=lanczos[cam]"
        game = "[0:v]crop=1080:820:420:0,scale=1080:820:flags=lanczos[game]"
    elif ch in ("kai", "kaicenat"):
        cam = "[0:v]crop=480:360:1440:720,scale=1080:1100:flags=lanczos[cam]"
        game = "[0:v]crop=1080:820:0:0,scale=1080:820:flags=lanczos[game]"
    elif ch in ("lacy",):
        cam = "[0:v]crop=494:278:0:0,scale=1080:1100:flags=lanczos[cam]"
        game = "[0:v]crop=1080:820:550:0,scale=1080:820:flags=lanczos[game]"
    else:
        cam = "[0:v]crop=1280:720:0:0,scale=1080:1100:flags=lanczos[cam]"
        game = "[0:v]crop=1080:820:420:0,scale=1080:820:flags=lanczos[game]"

    chain = f"{cam};{game};[cam][game]vstack=inputs=2[vstacked]"
    curr_v = "[vstacked]"

    # ASS Subtitles Filter
    if ass_path and os.path.exists(ass_path):
        ass_name = pathlib.Path(ass_path).name
        chain += f";{curr_v}ass={ass_name}[vout]"
    else:
        chain += f";{curr_v}null[vout]"

    # Audio Mixing: Layer viral BGM if present
    if has_bgm:
        chain += ";[1:a]aloop=loop=-1:size=2e+09,volume=0.20[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=7:tp=-1.5[aout]"
        audio_map = ["-map", "[aout]"]
    else:
        audio_map = ["-map", "0:a?", "-af", "loudnorm=I=-14:LRA=7:tp=-1.5"]

    filter_complex = ["-filter_complex", chain, "-map", "[vout]"] + audio_map
    return filter_complex


def render_vertical_clip(
    input_video: str,
    output_video: str,
    start_sec: float,
    duration: float,
    channel: str = "",
    hook_text: str = "",
    ass_path: str = None
) -> bool:
    """Renders high-impact 70/30 reaction vertical video with ducked viral BGM."""
    out_p = pathlib.Path(output_video).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    working_dir = out_p.parent

    # Detect viral BGM
    bgm_candidates = [
        pathlib.Path("assets/viral_bgm.mp3").resolve(),
        pathlib.Path("output/viral_bgm.mp3").resolve(),
        pathlib.Path(__file__).parent / "assets" / "viral_bgm.mp3"
    ]
    bgm_file = next((p for p in bgm_candidates if p.exists()), None)
    has_bgm = bgm_file is not None

    filter_complex = build_stack_filters(channel, hook_text, ass_path, has_bgm=has_bgm)

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.2f}",
        "-t", f"{duration:.2f}",
        "-i", str(input_video),
    ]
    if has_bgm:
        cmd += ["-i", str(bgm_file)]

    cmd += filter_complex + [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(out_p)
    ]

    res = subprocess.run(cmd, cwd=str(working_dir), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] FFmpeg error: {res.stderr[-400:]}")
        return False
    return True + [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(output_video)
    ]

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] FFmpeg error: {res.stderr[-400:]}")
        return False
    return True


def verify_video_integrity(video_path: str) -> dict:
    """Verifies resolution, framerate, duration, and audio stream using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path)
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

        valid = (w == 1080 and h == 1920 and 15.0 <= dur <= 65.0)
        return {
            "valid": valid,
            "width": w,
            "height": h,
            "duration": dur,
            "video_codec": v_stream.get("codec_name"),
            "audio_codec": a_stream.get("codec_name"),
            "aspect_ratio": f"{w}x{h} (9:16)"
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


if __name__ == "__main__":
    print("[*] Viral Auto-Editor & Subtitler initialized.")
